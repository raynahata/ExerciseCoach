import os
import re
import sys
import time
import rospy
import openai
import asyncio
import string
from datetime import datetime
from std_msgs.msg import String
from AWS_STT import start_transcription
from conv_logger import log_conversation

class PepperIntroSession:
    def __init__(self, participant_number=0, week_number=0):
        self.participant_number = participant_number
        self.week_number = week_number
        self.messages = []
        self.pepper_state = "listening"

        rospy.init_node("robot_speech_publisher", anonymous=True)

        self.speech_pub = rospy.Publisher("/gpt_speech", String, queue_size=10)
        self.display_pub = rospy.Publisher("/speech_display", String, queue_size=10)
        self.exercise_pub = rospy.Publisher("/exercise_command", String, queue_size=10)
        self.video_pub = rospy.Publisher("/pepper_video_control", String, queue_size=10)

        rospy.Subscriber("pepper_state", String, self._callback_state)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_filename = f"participant_{participant_number}_week_{week_number}.csv"
        self.csv_filepath = os.path.join(self.base_dir, "conversation_files", self.csv_filename)

        self.api_key = self._get_openai_key()
        self.client = openai.OpenAI(api_key=self.api_key)

        self._initialize_csv()
        self.initial_prompt = self._get_prompt("intro_prompt" if week_number == 0 else "intro_prompt_reccuring")
        self.messages = [{"role": "system", "content": self.initial_prompt}]

    def _callback_state(self, data):
        self.pepper_state = data.data

    def _get_openai_key(self):
        key_path = os.path.join(self.base_dir, "chatGPT.key")
        with open(key_path, 'r') as f:
            return f.read().strip()

    def _initialize_csv(self):
        if not os.path.isfile(self.csv_filepath):
            log_conversation("System", "Conversation log initialized", csv_file=self.csv_filename)

    def _get_prompt(self, prompt_name):
        prompt_file = os.path.join(self.base_dir, "prompts", prompt_name)
        with open(prompt_file, 'r') as file:
            return file.read()

    def parse_robot_response(self, response):
        match = re.match(r'^\{(.+?),\s*(true|false)\}$', response, re.IGNORECASE)
        if match:
            spoken_response, boolean_str = match.groups()
            spoken_response = spoken_response.strip().strip('"')
            ready_to_start = boolean_str.lower() == 'true'
            return spoken_response, ready_to_start
        return response.strip(), False

    def send_to_pepper(self, text):
        rospy.loginfo(f"Sending to Pepper: {text}")
        self.speech_pub.publish(text)
        self.pepper_state = "speaking"

    def send_to_display(self, text):
        rospy.loginfo(f"Displaying on Pepper: {text}")
        self.display_pub.publish(text)

    def send_exercise_command(self, text):
        rospy.loginfo(f"Sending exercise command: {text}")
        self.exercise_pub.publish(String(text))
        rospy.sleep(1)

    def start_video_recording(self):
        msg = f"start recording;participant_{self.participant_number};week_{self.week_number};intro"
        self.video_pub.publish(msg)

    def stop_video_recording(self):
        self.video_pub.publish("stop recording")

    async def generate_conversational_phrase(self):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=self.messages,
                max_tokens=100,
                temperature=0.7,
                n=1
            )
            phrase = response.choices[0].message.content.strip()
            log_conversation("Robot", phrase, csv_file=self.csv_filename)
            return phrase
        except Exception as e:
            print(f"OpenAI error: {e}")
            return None

    async def run_intro_session(self):
        print("Starting the intro session...")

        self.start_video_recording()

        # Initial GPT response
        initial_response = await self.generate_conversational_phrase()
        spoken_response, ready_to_start = self.parse_robot_response(initial_response)
        self.send_to_pepper(spoken_response)
        self.messages.append({"role": "assistant", "content": spoken_response})

        done_chat = False

        try:
            while not done_chat:
                if self.pepper_state == "listening":
                    print("Waiting for user response...")
                    try:
                        user_message = await asyncio.wait_for(start_transcription(), timeout=40)
                        log_conversation("User", user_message, csv_file=self.csv_filename)
                        print("You:", user_message)

                        if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                            print("Ending conversation.")
                            break

                        self.messages.append({"role": "user", "content": user_message})
                        bot_response = await self.generate_conversational_phrase()
                        spoken_response, ready_to_start = self.parse_robot_response(bot_response)

                        if spoken_response:
                            self.send_to_pepper(spoken_response)
                            self.messages.append({"role": "assistant", "content": spoken_response})

                            if ready_to_start:
                                print("User is ready to start exercising.")
                                break
                    except asyncio.TimeoutError:
                        print("Timeout: No user response within 40 seconds.")
                        break
        finally:
            self.stop_video_recording()


async def main():
    participant_number = 0
    week_number = 0

    session = PepperIntroSession(participant_number, week_number)
    await session.run_intro_session()

if __name__ == "__main__":
    asyncio.run(main())
