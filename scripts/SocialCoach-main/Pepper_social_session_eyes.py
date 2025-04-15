import openai
import os
import sys
import re
import time
import asyncio
import string
from datetime import datetime, timezone, timedelta

import rospy
from std_msgs.msg import String, Bool

from AWS_STT import start_transcription
from conv_logger import log_conversation


class PepperExerciseSession:
    def __init__(self):

        #CHANGE AT START
        self.participant_number = 0
        self.week_number = 0
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
        full_path = os.path.join(base_dir, "conversation_files", filename)
        if not os.path.isfile(full_path):
            log_conversation("System", "Conversation log initialized", csv_file=filename)
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
            print(f"[WAITING] is_pepper_speaking = {self.is_pepper_speaking}")
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
                print("Let's take a rest for 40 seconds.")
                log_conversation("Robot", "Take a rest for 40 seconds.", self.csv_history_file)
                rest_start = datetime.now(EST)

                while (datetime.now(EST) - rest_start).total_seconds() < 10:
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

        self.send_to_pepper("Great job completing this round!")
        self.send_exercise_command("rest")
        print("Great job completing this round!")
        log_conversation("Robot", "Great job completing this round!", self.csv_history_file)

        final_phrase = await self.generate_conversational_phrase()
        if final_phrase:
            self.send_to_pepper(final_phrase)
            log_conversation("Robot", final_phrase, self.csv_history_file)
            self.messages.append({"role": "assistant", "content": final_phrase})
            await self.wait_until_done_speaking()
        

        self.shutdown_pub.publish(Bool(data=True))


if __name__ == "__main__":
    session = PepperExerciseSession()
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

# def get_tts_status_callback(msg):
    
#     global is_pepper_speaking
#     is_pepper_speaking = msg.data

    

# is_pepper_speaking = False
# rospy.Subscriber('/pepper/tts_status', Bool,get_tts_status_callback)
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


# async def exercise_session(messages, exercise_list, csv_history_file):
#     current_set = 0
        
#     EST = timezone(timedelta(hours=-5))  # Define the EST timezone
#     global pepper_state

#     while current_set < 4:  # 4 sets in each round
#         #sp.text_to_speech(f"Let's do some {exercise_list[current_set]}.")
       
#         inittime = datetime.now(EST)
#         if current_set == 0:
#             pepper_speech=f"I'm super excited to exercise with you. Let's do some {exercise_list[current_set]}. Do you have anything fun planned for the day? "
#             send_to_pepper(pepper_speech)
#             last_speaker="robot"
#         else:
#             pepper_speech=f"Let's do some {exercise_list[current_set]}."
#             send_to_pepper_dispay_only(pepper_speech)
        
        
#         messages.append({"role": "system", "content": pepper_speech})
#         send_exercise_to_pepper(exercise_list[current_set])
#         # Exercise phase (20 seconds)
#         while (datetime.now(EST) - inittime).total_seconds() < 40:
            
            
           
#             # print(f"Pepper state = {pepper_state}")
#             if last_speaker == "robot" :
#                 try:
#                     # Wait for user response
#                     print(is_pepper_speaking)
#                     rate=rospy.Rate(10)
#                     while is_pepper_speaking==True:
                    
#                         rate.sleep()
#                     print(is_pepper_speaking)
#                     print("Waiting for user response...")
#                     user_message = await asyncio.wait_for(start_transcription(), timeout=50)
                    
#                     log_conversation("User", user_message, csv_file=csv_history_file)
#                     print("You:", user_message)
#                     if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
#                         #sp.text_to_speech("Ending session.")
#                         robot_response="Thank you for exercising with me."
#                         send_to_pepper(robot_response)
#                         send_exercise_to_pepper("rest")
#                         log_conversation("Robot", robot_response, csv_file=csv_history_file)
#                         print("Ending session.")
#                         shutdown_publisher.publish(Bool(data=True))
#                         return  # Exit early if the user ends the session

#                     # Update last speaker and append the message
#                     last_speaker = "user"
#                     messages.append({"role": "user", "content": user_message})
#                 except asyncio.TimeoutError:
#                     # Handle timeout case
#                     print("Timeout: No user response detected within 20 seconds.")
#                     last_speaker == "robot"

#             elif last_speaker == "user":
#                 # Generate and speak robot response
#                 conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)

            
#                 #sp.text_to_speech(conversational_phrase)
#                 send_to_pepper(conversational_phrase)
                
#                 messages.append({"role": "assistant", "content": conversational_phrase})
#                 log_conversation("Robot", conversational_phrase, csv_history_file)

#                 # Update last speaker
#                 last_speaker = "robot"

#         # End of the set
#         #sp.text_to_speech("Done with the set.")
#         send_to_pepper_dispay_only("Done with the set.")
#         log_conversation("Robot", "Done with the set.", csv_history_file)
#         send_exercise_to_pepper("rest")
#         messages.append({"role": "system", "content": "Done with the set."})
#         current_set += 1

#         # Rest phase (40 seconds)
#         if current_set < 4:
#             #sp.text_to_speech("Take a rest for 40 seconds.")
#             rest_mesaage="Let's take a rest for 40 seconds."
#             messages.append({"role": "system", "content": rest_mesaage})
#             send_to_pepper_dispay_only(rest_mesaage)    
#             log_conversation("Robot","Take a rest for 40 seconds.", csv_history_file)
#             send_exercise_to_pepper("rest")
#             rest_start_time = datetime.now(EST)
#             while (datetime.now(EST) - rest_start_time).total_seconds() < 10:
#                 # print(f"Pepper state = {pepper_state}")
#                 if last_speaker == "robot":
#                     try:
#                         # Wait for user response
#                         # user_message = await start_transcription()
#                         while is_pepper_speaking:
#                             rospy.sleep(0.5)
                        
#                         user_message = await asyncio.wait_for(start_transcription(), timeout=50)
#                         print("Waiting for user response...")
#                         log_conversation("User", user_message, csv_file=csv_history_file)
#                         print("You:", user_message)
                        
#                         if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
#                             #sp.text_to_speech("Ending session.")
#                             robot_response="Thank you for exercising with me."
#                             send_to_pepper(robot_response)
#                             send_exercise_to_pepper("rest")
#                             log_conversation("Robot", robot_response, csv_file=csv_history_file)
#                             print("Ending session.")
#                             shutdown_publisher.publish(Bool(data=True))
#                             return  # Exit early if the user ends the session

#                         # Update last speaker and append the message
#                         last_speaker = "user"
#                         messages.append({"role": "user", "content": user_message})
#                     except asyncio.TimeoutError:
#                         # Handle timeout case
#                         print("Timeout: No user response detected within 20 seconds.")
#                         last_speaker == "robot"

#                 elif last_speaker == "user":
#                     # Generate and speak robot response
#                     conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)
                    
#                     #sp.text_to_speech(conversational_phrase)
#                     send_to_pepper(conversational_phrase)
#                     messages.append({"role": "assistant", "content": conversational_phrase})
#                     log_conversation("Robot",conversational_phrase, csv_file=csv_history_file)
                    
#                     # Update last speaker
#                     last_speaker = "robot"
#         if current_set==4:
#     #sp.text_to_speech("Great job completing this round!")
    
#             send_to_pepper("Great job completing this round!")
#             send_exercise_to_pepper("rest")

#             messages.append({"role": "system", "content": "Great job completing this round!"})
#             log_conversation("Robot","Great job completing this round!", csv_file=csv_history_file)
#             shutdown_publisher.publish(Bool(data=True))
#             break
#     #sp.text_to_speech("Great job completing this round!")
    
#     # send_to_pepper("Great job completing this round!")
#     # send_exercise_to_pepper("rest")

#     # messages.append({"role": "system", "content": "Great job completing this round!"})
#     # log_conversation("Robot","Great job completing this round!", csv_file=csv_history_file)
                
  
  
# async def main():
#     participant_number = 0
#     week_number=0

#     csv_filename = f"participant_{participant_number}_week_{week_number}.csv"

#     #initializing the CSV files 
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     initialize_csv(csv_filename)
#     csv_history_file = os.path.join(base_dir, "conversation_files",csv_filename)
    
#     if week_number == 0:
#         conversational_prompt = "conversational_prompt_0.txt"
#     else:
#         conversational_prompt=f"conversational_prompt_{participant_number}_week_{week_number}.txt"

    
#     conversational_prompt=get_prompt(conversational_prompt)

#     conversational_messages = [{"role": "system", "content": conversational_prompt}]



#     video_control_pub.publish(f"start recording;participant_{participant_number};week_{week_number};exercise")


    
#     # Wake word detection
#     ready_statement= "When you are ready to exercise, please say 'ready'."
#     send_to_pepper_dispay_only(ready_statement)
#     await listen_for_wake_word(wake_word="ready")

  
#     print("Starting the intro session...")
#     #intro_messages=await intro_session(messages, csv_history_file)
    
#     print("Starting the exercise session...")
#     exercise_list = ["bicep curls", "bicep curls", "lateral raises", "lateral raises"]
#     await exercise_session(conversational_messages, exercise_list, csv_history_file)
#     video_control_pub.publish("stop_video")

# if __name__ == "__main__":
#     asyncio.run(main())
