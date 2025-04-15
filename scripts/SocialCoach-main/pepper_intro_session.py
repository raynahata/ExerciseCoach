
import openai
import os
import sys
import re
import time
import asyncio
import string
from datetime import datetime

import rospy
from std_msgs.msg import String, Bool

from AWS_STT import start_transcription
from conv_logger import log_conversation


class PepperIntroSession:
    def __init__(self):
        
        #CHANGE AT START
        self.participant_number = 0
        self.week_number = 0
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
        full_path = os.path.join(base_dir, "conversation_files", filename)
        if not os.path.isfile(full_path):
            log_conversation("System", "Conversation log initialized", csv_file=filename)
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

# import openai
# import os
# import asyncio
# from AWS_STT import start_transcription  # Import the transcription function
# from conv_logger import log_conversation
# import string
# from gtts import gTTS
# import speech as sp
# import pvporcupine
# import pyaudio
# from datetime import datetime, timezone, timedelta
# import re
# import time 
# import rospy
# from std_msgs.msg import String
# from std_msgs.msg import Bool
# import sys

# # Initialize OpenAI client
# apikey = None
# access_key="ErK9WB5nNekaAlns1cldvwAU8rQSB8JPkF1QkhNfwO9vNA5FS7ihmA=="

# rospy.init_node("robot_speech_publisher", anonymous=True)
# pepper_state = "listening"

# def callback_state(data):
#     """
#     Callback for 'pepper_state' topic.
#     """
#     global pepper_state
#     rospy.loginfo("Received state: {}".format(data.data))
#     pepper_state = data.data


# speech_publisher = rospy.Publisher("/gpt_speech", String, queue_size=10)
# display_publisher = rospy.Publisher("/speech_display", String, queue_size=10)
# exercise_publisher = rospy.Publisher("/exercise_command", String, queue_size=10)
# video_control_pub = rospy.Publisher("/pepper_video_control", String, queue_size=10)
# shutdown_publisher = rospy.Publisher("/controller_shutdown", Bool, queue_size=10)

# rospy.Subscriber("pepper_state", String, callback_state)




# def getkey():
#     global apikey
#     if not apikey:
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         key_file = os.path.join(base_dir, "chatGPT.key")
#         if not os.path.exists(key_file):
#             raise FileNotFoundError(f"API key file not found at {key_file}")
#         with open(key_file, 'r') as keyfile:
#             apikey = keyfile.read().strip()
#     return apikey

# client = openai.OpenAI(api_key=getkey())

# def send_to_pepper(text):
#     """
#     Sends GPT-generated text to Pepper via ROS topic.
#     """
#     rospy.loginfo("Sending to Pepper: {}".format(text))
#     speech_publisher.publish(text)
#     global pepper_state
#     pepper_state = "speaking"

# def send_to_pepper_dispay_only(text):
#     """
#     Sends GPT-generated text to Pepper via ROS topic.
#     """
#     rospy.loginfo("Sending to Pepper: {}".format(text))
#     display_publisher.publish(text)

# def send_exercise_to_pepper(text):
#     """
#     Sends GPT-generated text to Pepper via ROS topic.
#     """
#     rospy.loginfo("Sending exercise Pepper: {}".format(text))
#     exercise_publisher.publish(String(text))
#     rospy.sleep(1)


# def parse_robot_response(response):
#     """
#     Parse the robot response string into a tuple of (spoken_response, ready_to_exercise).

#     Args:
#         response (str): Robot's response string in the format '{"spoken_phrase", boolean}'.

#     Returns:
#         tuple: (spoken_response (str), ready_to_exercise (bool)).
#                If parsing fails, returns (response (str), False).
#     """
#     # Regular expression to match the structure '{Spoken_response, Boolean}'
#     match = re.match(r'^\{(.+?),\s*(true|false)\}$', response, re.IGNORECASE)
#     if match:
#         spoken_response, boolean_str = match.groups()
#         spoken_response = spoken_response.strip().strip('"')  # Remove extra spaces and quotes
#         ready_to_exercise = boolean_str.strip().lower() == 'true'  # Convert to boolean
#         return spoken_response, ready_to_exercise

#     # If parsing fails, return the raw response and False
#     return response.strip(), False


# async def generate_conversational_phrase(messages, csv_history_file):
#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=messages,
#             max_tokens=100,
#             temperature=0.7,
#             n=1
#         )
#         conversational_phrase = response.choices[0].message.content.strip()
#         log_conversation("Robot", conversational_phrase, csv_file=csv_history_file)
#         print("Robot:", conversational_phrase)
#         return conversational_phrase
#     except Exception as e:
#         print(f"Error: {e}")
#         return None


# async def listen_for_wake_word(wake_word="hello", timeout=20):
#     """
#     Uses AWS Transcribe to listen for a wake word in real-time.    Args:
#         wake_word (str): The phrase to trigger the system.
#         timeout (int): Time in seconds before the script shuts down if no speech is detected.
#     """
#     print("Listening for wake word...")
#     last_detection_time = time.time()  # Start tracking time    
#     while True:
#         # Run transcription in the background
#         transcription_task = asyncio.create_task(start_transcription())        
#         while not transcription_task.done():
#             await asyncio.sleep(1)  # Non-blocking wait            # Check for timeout
#             if time.time() - last_detection_time > timeout:
#                 print("No speech detected for 3 minutes. Shutting down...")
#                 sys.exit(0)  # Exit the script        # Get transcribed text once available
#         transcribed_text = transcription_task.result()        
#         if transcribed_text:
#             print(transcribed_text)
#             last_detection_time = time.time()  # Reset timeout            # Normalize and check if the wake word is present
#             normalized_text = transcribed_text.lower().strip()
#             if wake_word in normalized_text:
#                 print("Wake word detected!")
#                 return  # Exit the function and continue execution
        
# def initialize_csv(conv_CSV_filename):
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     conversational_CSV_filepath = os.path.join(base_dir,"conversation_files", conv_CSV_filename)
#     if not os.path.isfile(conversational_CSV_filepath):
#         log_conversation("System", "Conversation log initialized", csv_file=conv_CSV_filename)

# def get_prompt(prompt_name):
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     prompt_template_file = os.path.join(base_dir,"prompts",prompt_name)
#     prompt=read_prompt_file(prompt_template_file)
#     return prompt

# def read_prompt_file(prompt_file):
#     with open(prompt_file, 'r') as file:
#         prompt_template = file.read()
#     return prompt_template




# async def intro_session(messages, csv_history_file,participant_number,week_number):
#     """
#     Handles the introduction session as per the flow described in the prompt.

#     Args:
#         messages (list): List of conversation messages.
#         csv_history_file (str): Path to the conversation log file.

#     Returns:
#         bool: True if the user is ready to start the exercise session, False otherwise.
#     """
    
#     done_chat=False
#     ready_to_start = False
#     print("Generating initial response...")
#     initial_response= await generate_conversational_phrase(messages, csv_history_file) 
#     spoken_response, ready_to_start = parse_robot_response(initial_response)
    
#     #sp.text_to_speech(spoken_response)
#     send_to_pepper(spoken_response)
#     log_conversation("Robot",spoken_response,csv_history_file)

#     if initial_response:
#         messages.append({"role": "assistant", "content": spoken_response})
    
#     try: 
#         while not done_chat:
#             if pepper_state == "listening":
#                 print("Waiting for user response...")
#                 # user_message=await start_transcription()
#                 user_message = await asyncio.wait_for(start_transcription(), timeout=40)
#                 log_conversation("User",user_message,csv_history_file)
#                 print("You:",user_message)
#                 if user_message.lower().replace(" ","").strip(string.punctuation)=="bye":
#                     done_chat=True
#                     shutdown_publisher.publish(Bool(data=True))
#                     print("Ending conversation.")
#                     break
#                 messages.append({"role":"user","content":user_message})
#                 conversational_response = await generate_conversational_phrase(messages, csv_history_file)
#                 spoken_response, ready_to_start = parse_robot_response(conversational_response)  # Parse the tuple
#                 if spoken_response:
#                     #sp.text_to_speech(spoken_response)
#                     send_to_pepper(spoken_response)
#                     messages.append({"role": "assistant", "content": spoken_response})

                
#                     # If the user is ready to start, end the intro session
#                     if ready_to_start==True:
#                         # print("User is ready to start the exercise session.")
#                         # sp.text_to_speech("Great! Let's begin the exercise session.")
#                         done_chat=True
#                         shutdown_publisher.publish(Bool(data=True))
#                         # print("Ending conversation.")
#                         # return messages
#                         break
#     except asyncio.TimeoutError:
#         # Handle timeout case
#         print("Intro Section Timeout: No user response detected within 20 seconds.")
                    
                
  
  
# async def main():
#     participant_number = 0
#     week_number=0

#     csv_filename = f"participant_{participant_number}_week_{week_number}.csv"

#     #initializing the CSV files 
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     initialize_csv(csv_filename)
#     csv_history_file = os.path.join(base_dir, "conversation_files",csv_filename)
    
#     #getting the prompts
#     if week_number==0:
#         initial_prompt=get_prompt("intro_prompt")
#     else:
#         initial_prompt=get_prompt("intro_prompt_reccuring")
   
#     messages = [{"role": "system", "content": initial_prompt}]
    


#     # Wake word detection
#     #await listen_for_wake_word()
#     video_control_pub.publish(f"start recording;participant_{participant_number};week_{week_number};intro")
    
#     print("Starting the intro session...")
    
#     await intro_session(messages, csv_history_file,participant_number,week_number)
#     video_control_pub.publish("stop_video")
    


# if __name__ == "__main__":
#     asyncio.run(main())
