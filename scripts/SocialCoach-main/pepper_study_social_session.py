import os
import sys
import re
import time
import rospy
import openai
import asyncio
import string
from datetime import datetime, timezone, timedelta
from std_msgs.msg import String
from AWS_STT import start_transcription
from conv_logger import log_conversation

class PepperExerciseSession:
    def __init__(self, participant_number, week_number):
        self.participant_number = participant_number
        self.week_number = week_number
        self.pepper_state = "listening"
        self.messages = []

        rospy.init_node("robot_speech_publisher", anonymous=True)

        self.speech_pub = rospy.Publisher("/gpt_speech", String, queue_size=10)
        self.display_pub = rospy.Publisher("/speech_display", String, queue_size=10)
        self.exercise_pub = rospy.Publisher("/exercise_command", String, queue_size=10)
        self.video_pub = rospy.Publisher("/pepper_video_control", String, queue_size=10)

        rospy.Subscriber("pepper_state", String, self._callback_state)
        self.api_key = self._get_openai_key()
        self.client = openai.OpenAI(api_key=self.api_key)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_filename = f"participant_{participant_number}_week_{week_number}.csv"
        self.csv_filepath = os.path.join(self.base_dir, "conversation_files", self.csv_filename)
        self._initialize_csv()

    def _callback_state(self, data):
        self.pepper_state = data.data

    def _get_openai_key(self):
        key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatGPT.key")
        if not os.path.exists(key_path):
            raise FileNotFoundError("chatGPT.key not found")
        with open(key_path, 'r') as f:
            return f.read().strip()

    def _initialize_csv(self):
        if not os.path.isfile(self.csv_filepath):
            log_conversation("System", "Conversation log initialized", csv_file=self.csv_filename)

    def send_to_pepper(self, text):
        self.speech_pub.publish(text)
        self.pepper_state = "speaking"

    def send_to_display(self, text):
        self.display_pub.publish(text)

    def send_exercise_command(self, text):
        self.exercise_pub.publish(String(text))
        rospy.sleep(1)

    def start_video_recording(self, session_type):
        msg = f"start recording;participant_{self.participant_number};week_{self.week_number};{session_type}"
        self.video_pub.publish(msg)

    def stop_video_recording(self):
        self.video_pub.publish("stop recording")

    def get_prompt(self):
        if self.week_number == 0:
            prompt_file = "conversational_prompt_0.txt"
        else:
            prompt_file = f"conversational_prompt_{self.participant_number}_week_{self.week_number}.txt"

        prompt_path = os.path.join(self.base_dir, "prompts", prompt_file)
        with open(prompt_path, 'r') as f:
            return f.read()

    def parse_robot_response(self, response):
        match = re.match(r'^\{(.+?),\s*(true|false)\}$', response, re.IGNORECASE)
        if match:
            spoken_response, boolean_str = match.groups()
            spoken_response = spoken_response.strip().strip('"')
            ready_to_exercise = boolean_str.lower() == 'true'
            return spoken_response, ready_to_exercise
        return response.strip(), False

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
            print(f"OpenAI Error: {e}")
            return None

    async def listen_for_wake_word(self, wake_word="ready", timeout=20):
        print("Listening for wake word...")
        last_detection = time.time()
        while True:
            task = asyncio.create_task(start_transcription())
            while not task.done():
                await asyncio.sleep(1)
                if time.time() - last_detection > timeout:
                    print("No speech detected. Shutting down...")
                    sys.exit(0)
            result = task.result()
            if result and wake_word in result.lower():
                print("Wake word detected!")
                return

    async def run_exercise_session(self, exercise_list):
        current_set = 0
        EST = timezone(timedelta(hours=-5))
        last_speaker = "robot"

        while current_set < 4:
            inittime = datetime.now(EST)
            exercise_name = exercise_list[current_set]

            if current_set == 0:
                phrase = f"I'm super excited to exercise with you. Let's do some {exercise_name}. Do you have anything fun planned for the day?"
                self.send_to_pepper(phrase)
            else:
                phrase = f"Let's do some {exercise_name}."
                self.send_to_display(phrase)

            self.messages.append({"role": "system", "content": phrase})
            self.send_exercise_command(exercise_name)

            while (datetime.now(EST) - inittime).total_seconds() < 40:
                if last_speaker == "robot":
                    try:
                        print("Waiting for user response...")
                        user_message = await asyncio.wait_for(start_transcription(), timeout=50)
                        log_conversation("User", user_message, csv_file=self.csv_filename)
                        if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                            self.send_to_pepper("Thank you for exercising with me.")
                            self.send_exercise_command("rest")
                            log_conversation("Robot", "Thank you for exercising with me.", csv_file=self.csv_filename)
                            return
                        last_speaker = "user"
                        self.messages.append({"role": "user", "content": user_message})
                    except asyncio.TimeoutError:
                        last_speaker = "robot"

                elif last_speaker == "user":
                    response = await self.generate_conversational_phrase()
                    self.send_to_pepper(response)
                    self.messages.append({"role": "assistant", "content": response})
                    last_speaker = "robot"

            self.send_to_display("Done with the set.")
            self.send_exercise_command("rest")
            log_conversation("Robot", "Done with the set.", csv_file=self.csv_filename)
            self.messages.append({"role": "system", "content": "Done with the set."})
            current_set += 1

            if current_set < 4:
                self.send_to_display("Let's take a rest for 40 seconds.")
                log_conversation("Robot", "Take a rest for 40 seconds.", csv_file=self.csv_filename)
                self.messages.append({"role": "system", "content": "Take a rest for 40 seconds."})
                rest_start = datetime.now(EST)

                while (datetime.now(EST) - rest_start).total_seconds() < 10:
                    if last_speaker == "robot" and self.pepper_state == "listening":
                        try:
                            print("Waiting for user response during rest...")
                            user_message = await asyncio.wait_for(start_transcription(), timeout=50)
                            log_conversation("User", user_message, csv_file=self.csv_filename)
                            if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                                self.send_to_pepper("Thank you for exercising with me.")
                                self.send_exercise_command("rest")
                                log_conversation("Robot", "Thank you for exercising with me.", csv_file=self.csv_filename)
                                return
                            last_speaker = "user"
                            self.messages.append({"role": "user", "content": user_message})
                        except asyncio.TimeoutError:
                            last_speaker = "robot"
                    elif last_speaker == "user":
                        response = await self.generate_conversational_phrase()
                        self.send_to_pepper(response)
                        self.messages.append({"role": "assistant", "content": response})
                        log_conversation("Robot", response, csv_file=self.csv_filename)
                        last_speaker = "robot"

        self.send_to_pepper("Great job completing this round!")
        self.send_exercise_command("rest")
        self.messages.append({"role": "system", "content": "Great job completing this round!"})
        log_conversation("Robot", "Great job completing this round!", csv_file=self.csv_filename)


async def main():
    participant_number = 0
    week_number = 0

    session = PepperExerciseSession(participant_number, week_number)

    session.start_video_recording("exercise")

    prompt = session.get_prompt()
    session.messages = [{"role": "system", "content": prompt}]

    session.send_to_display("When you are ready to exercise, please say 'ready'.")
    await session.listen_for_wake_word(wake_word="ready")

    exercise_list = ["bicep curls", "bicep curls", "lateral raises", "lateral raises"]
    await session.run_exercise_session(exercise_list)

    session.stop_video_recording()

if __name__ == "__main__":
    asyncio.run(main())
