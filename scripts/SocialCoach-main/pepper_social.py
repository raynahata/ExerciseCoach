import openai
import os
import sys
import re
import time
import asyncio
import string
from datetime import datetime, timezone, timedelta

import rospy
import yaml
from std_msgs.msg import String, Bool

from AWS_STT import start_transcription
from conv_logger import log_conversation
from summary_generator import generate_summary_for_session


def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


class PepperExerciseSession:
    def __init__(self):

        params = load_config()
        self.participant_number = int(params.get("participant_number", 0))
        self.week_number = int(params.get("week_number", 0))
        self.generate_summary_after_session = bool(params.get("generate_summary_after_session", False))
        self.summary_prompt_file = params.get("summary_prompt_file", "summaryPrompt.txt")
        self.summary_model = params.get("summary_model", "gpt-4o")
        self.summary_max_tokens = int(params.get("summary_max_tokens", 250))
        self.pepper_state = "listening"
        self.is_pepper_speaking = False
        self.apikey = None
        self.client = openai.OpenAI(api_key=self.getkey())

        rospy.init_node("robot_speech_publisher", anonymous=True)

        rospy.Subscriber("/pepper/tts_status", Bool, self.tts_status_callback)
        rospy.Subscriber("pepper_state", String, self.state_callback)

        self.speech_pub = rospy.Publisher("/gpt_speech", String, queue_size=10)
        self.display_pub = rospy.Publisher("/speech_display", String, queue_size=10)
        self.exercise_pub = rospy.Publisher("/exercise_command", String, queue_size=10)
        self.video_pub = rospy.Publisher("/pepper_video_control", String, queue_size=10)
        self.shutdown_pub = rospy.Publisher("/controller_shutdown", Bool, queue_size=10)

        self.csv_history_file = self.initialize_csv_file()
        self.messages = [{"role": "system", "content": self.load_prompt()}]

    def getkey(self):
        if not self.apikey:
            key_path = os.path.join(os.path.dirname(__file__), "chatGPT.key")
            with open(key_path, "r") as f:
                self.apikey = f.read().strip()
        return self.apikey

    def tts_status_callback(self, msg):
        self.is_pepper_speaking = msg.data
        print(f"[ROS FLAG] is_pepper_speaking = {msg.data}")

    def state_callback(self, msg):
        self.pepper_state = msg.data
        rospy.loginfo(f"Received state: {msg.data}")

    def send_to_pepper(self, text):
        print(f"Sending to Pepper: {text}")
        self.is_pepper_speaking = True 
        self.speech_pub.publish(text)
        self.pepper_state = "speaking"

    def send_display_only(self, text):
        print(f"Displaying on Pepper: {text}")
        self.display_pub.publish(text)

    def send_exercise_command(self, text):
        print(f"Sending exercise command: {text}")
        self.exercise_pub.publish(String(data=text))
        rospy.sleep(1)

    def initialize_csv_file(self):
        filename = f"participant_{self.participant_number}_week_{self.week_number}.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        conversation_dir = os.path.join(base_dir, "conversation_files")
        os.makedirs(conversation_dir, exist_ok=True)
        full_path = os.path.join(conversation_dir, filename)
        if not os.path.isfile(full_path):
            log_conversation("System", "Conversation log initialized", csv_file=full_path)
        return full_path

    def load_prompt(self):
        prompt_name = "conversational_prompt_0.txt" if self.week_number == 0 else f"conversational_prompt_{self.participant_number}_week_{self.week_number}.txt"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(base_dir, "prompts", prompt_name)
        with open(prompt_path, "r") as f:
            return f.read()

    async def wait_until_done_speaking(self):
        rate = rospy.Rate(10)
        while self.is_pepper_speaking:
           # print(f"[WAITING] is_pepper_speaking = {self.is_pepper_speaking}")
            rate.sleep()

    async def generate_conversational_phrase(self):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=self.messages,
                max_tokens=100,
                temperature=0.7,
                n=1
            )
            text = response.choices[0].message.content.strip()
            print("Robot:", text)
            log_conversation("Robot", text, csv_file=self.csv_history_file)
            return text
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return None

    async def listen_for_wake_word(self, wake_word="hello", timeout=20):
        print("Listening for wake word...")
        last_detection_time = time.time()
        while True:
            transcription_task = asyncio.create_task(start_transcription())
            while not transcription_task.done():
                await asyncio.sleep(1)
                if time.time() - last_detection_time > timeout:
                    print("No speech detected. Shutting down.")
                    sys.exit(0)
            transcribed_text = transcription_task.result()
            if transcribed_text:
                print("Transcript:", transcribed_text)
                last_detection_time = time.time()
                if wake_word in transcribed_text.lower():
                    print("Wake word detected!")
                    return

    async def run(self):
        self.video_pub.publish(f"start recording;participant_{self.participant_number};week_{self.week_number};exercise")
        self.send_display_only("When you are ready to exercise, please say 'ready'.")
        await self.listen_for_wake_word("ready")

        print("Starting the exercise session...")
        exercise_list = ["bicep curls", "bicep curls", "lateral raises", "lateral raises"]
        await self.exercise_session(exercise_list)
        self.video_pub.publish("stop_video")
        self.maybe_generate_session_summary()

    def maybe_generate_session_summary(self):
        if not self.generate_summary_after_session:
            print("Automatic summary generation is disabled.")
            return

        print("Generating automatic session summary...")
        summary_path = generate_summary_for_session(
            self.participant_number,
            self.week_number,
            csv_filepath=self.csv_history_file,
            prompt_filename=self.summary_prompt_file,
            model=self.summary_model,
            max_tokens=self.summary_max_tokens
        )

        if summary_path:
            print(f"Automatic summary saved to {summary_path}")
        else:
            print("Automatic summary generation did not produce a file.")

    async def exercise_session(self, exercise_list):
        current_set = 0
        EST = timezone(timedelta(hours=-5))
        last_speaker = "robot"

        while current_set < 4:
            start_time = datetime.now(EST)

            if current_set == 0:
                msg = f"I'm super excited to exercise with you. Let's do some {exercise_list[current_set]}. Do you have anything fun planned for the day?"
                self.send_to_pepper(msg)
            else:
                msg = f"Let's do some {exercise_list[current_set]}."
                self.send_display_only(msg)

            self.messages.append({"role": "system", "content": msg})
            self.send_exercise_command(exercise_list[current_set])

            while (datetime.now(EST) - start_time).total_seconds() < 40:
                if last_speaker == "robot":
                    await self.wait_until_done_speaking()
                    try:
                        print("Waiting for user response...")
                        user_input = await asyncio.wait_for(start_transcription(), timeout=50)
                        print("You:", user_input)
                        log_conversation("User", user_input, csv_file=self.csv_history_file)

                        if user_input.lower().replace(" ", "").strip(string.punctuation) == "bye":
                            print("Ending session.")
                            self.send_to_pepper("Thank you for exercising with me.")
                            self.send_exercise_command("rest")
                            self.shutdown_pub.publish(Bool(data=True))
                            return

                        self.messages.append({"role": "user", "content": user_input})
                        last_speaker = "user"
                    except asyncio.TimeoutError:
                        print("Timeout: No user response detected.")
                        last_speaker = "robot"
                else:
                    robot_response = await self.generate_conversational_phrase()
                    self.send_to_pepper(robot_response)
                    self.messages.append({"role": "assistant", "content": robot_response})
                    last_speaker = "robot"

            self.send_display_only("Done with the set.")
            self.send_exercise_command("rest")
            print("Done with the set.")
            log_conversation("Robot", "Done with the set.", self.csv_history_file)
            self.messages.append({"role": "system", "content": "Done with the set."})
            current_set += 1

            if current_set < 4:
                self.send_display_only("Let's take a rest for 40 seconds.")
                self.send_exercise_command("rest")
                rospy.sleep(1)
                print("Let's take a rest for 40 seconds.")
                log_conversation("Robot", "Take a rest for 40 seconds.", self.csv_history_file)
                rest_start = datetime.now(EST)

                while (datetime.now(EST) - rest_start).total_seconds() < 40:
                    if last_speaker == "robot":
                        await self.wait_until_done_speaking()
                        try:
                            print("Waiting for user response...")
                            user_input = await asyncio.wait_for(start_transcription(), timeout=50)
                            print("You:", user_input)
                            log_conversation("User", user_input, csv_file=self.csv_history_file)

                            if user_input.lower().replace(" ", "").strip(string.punctuation) == "bye":
                                print("Ending session.")
                                self.send_to_pepper("Thank you for exercising with me.")
                                self.send_exercise_command("rest")
                                self.shutdown_pub.publish(Bool(data=True))
                                return

                            self.messages.append({"role": "user", "content": user_input})
                            last_speaker = "user"
                        except asyncio.TimeoutError:
                            print("Timeout: No user response detected.")
                            last_speaker = "robot"
                    else:
                        robot_response = await self.generate_conversational_phrase()
                        self.send_to_pepper(robot_response)
                        self.messages.append({"role": "assistant", "content": robot_response})
                        last_speaker = "robot"
           

        self.send_to_pepper("Great job completing this round!Please fill out the survey!")
        self.send_exercise_command("rest")
        print("Great job completing this round!")
        log_conversation("Robot", "Great job completing this round!Please fill out the survey!", self.csv_history_file)

       
        await self.wait_until_done_speaking()
        

        self.shutdown_pub.publish(Bool(data=True))


if __name__ == "__main__":
    session = PepperExerciseSession()
    asyncio.run(session.run())
