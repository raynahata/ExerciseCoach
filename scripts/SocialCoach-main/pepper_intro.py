
import openai
import os
import sys
import re
import time
import asyncio
import string
from datetime import datetime

import rospy
import yaml
from std_msgs.msg import String, Bool

from AWS_STT import start_transcription
from conv_logger import log_conversation


def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


class PepperIntroSession:
    def __init__(self):
        
        params = load_config()
        self.participant_number = int(params.get("participant_number", 0))
        self.week_number = int(params.get("week_number", 0))
        self.pepper_state = "listening"
        self.is_pepper_speaking = False
        self.apikey = None
        self.client = openai.OpenAI(api_key=self.getkey())

        rospy.init_node("robot_intro_session", anonymous=True)

        rospy.Subscriber("/pepper/tts_status", Bool, self.tts_status_callback)
        rospy.Subscriber("pepper_state", String, self.state_callback)

        self.speech_pub = rospy.Publisher("/gpt_speech", String, queue_size=10)
        self.display_pub = rospy.Publisher("/speech_display", String, queue_size=10)
        self.exercise_pub = rospy.Publisher("/exercise_command", String, queue_size=10)
        self.video_pub = rospy.Publisher("/pepper_video_control", String, queue_size=10)
        self.shutdown_pub = rospy.Publisher("/controller_shutdown", Bool, queue_size=10)

        self.csv_history_file = self.initialize_csv()
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

    def initialize_csv(self):
        filename = f"participant_{self.participant_number}_week_{self.week_number}.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        conversation_dir = os.path.join(base_dir, "conversation_files")
        os.makedirs(conversation_dir, exist_ok=True)
        full_path = os.path.join(conversation_dir, filename)
        if not os.path.isfile(full_path):
            log_conversation("System", "Conversation log initialized", csv_file=full_path)
        return full_path

    def load_prompt(self):
        prompt_name = "intro_prompt" if self.week_number == 0 else "intro_prompt_reccuring"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(base_dir, "prompts", prompt_name)
        with open(prompt_path, "r") as f:
            return f.read()

    def parse_robot_response(self, response):
        match = re.match(r'^\{(.+?),\s*(true|false)\}$', response, re.IGNORECASE)
        if match:
            spoken_response, boolean_str = match.groups()
            spoken_response = spoken_response.strip().strip('"')
            ready_to_exercise = boolean_str.strip().lower() == 'true'
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
            text = response.choices[0].message.content.strip()
            log_conversation("Robot", text, csv_file=self.csv_history_file)
            print("Robot:", text)
            return text
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return None

    async def run_intro_session(self):
        done_chat = False
        print("Generating initial response...")
        initial_response = await self.generate_conversational_phrase()
        spoken_response, ready_to_start = self.parse_robot_response(initial_response)
        self.send_to_pepper(spoken_response)
        log_conversation("Robot", spoken_response, self.csv_history_file)
        self.messages.append({"role": "assistant", "content": spoken_response})

        try:
            while not done_chat:
                if self.pepper_state == "listening" and not self.is_pepper_speaking:
                    print("Waiting for user response...")
                    user_message = await asyncio.wait_for(start_transcription(), timeout=40)
                    log_conversation("User", user_message, self.csv_history_file)
                    print("You:", user_message)

                    if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                        print("Ending conversation.")
                        self.shutdown_pub.publish(Bool(data=True))
                        return

                    self.messages.append({"role": "user", "content": user_message})
                    robot_response = await self.generate_conversational_phrase()
                    spoken_response, ready_to_start = self.parse_robot_response(robot_response)
                    if spoken_response:
                        self.send_to_pepper(spoken_response)
                        self.messages.append({"role": "assistant", "content": spoken_response})

                    if ready_to_start:
                        print("User is ready to start exercise session.")
                        self.shutdown_pub.publish(Bool(data=True))
                        done_chat = True
        except asyncio.TimeoutError:
            print("Intro Section Timeout: No user response detected.")

    async def run(self):
        self.video_pub.publish(f"start recording;participant_{self.participant_number};week_{self.week_number};intro")
        await self.run_intro_session()
        self.video_pub.publish("stop_video")


if __name__ == "__main__":
    session = PepperIntroSession()
    asyncio.run(session.run())
