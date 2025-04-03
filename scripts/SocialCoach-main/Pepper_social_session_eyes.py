
import openai
import os
import asyncio
from AWS_STT import start_transcription  # Import the transcription function
from conv_logger import log_conversation
import string
from gtts import gTTS
import speech as sp
import pvporcupine
import pyaudio
from datetime import datetime, timezone, timedelta
import re
import time 
import rospy
from std_msgs.msg import String
from std_msgs.msg import Bool
import sys

# Initialize OpenAI client
apikey = None
access_key="ErK9WB5nNekaAlns1cldvwAU8rQSB8JPkF1QkhNfwO9vNA5FS7ihmA=="

rospy.init_node("robot_speech_publisher", anonymous=True)
pepper_state = "listening"

def callback_state(data):
    """
    Callback for 'pepper_state' topic.
    """
    global pepper_state
    rospy.loginfo("Received state: {}".format(data.data))
    pepper_state = data.data


speech_publisher = rospy.Publisher("/gpt_speech", String, queue_size=10)
display_publisher = rospy.Publisher("/speech_display", String, queue_size=10)
exercise_publisher = rospy.Publisher("/exercise_command", String, queue_size=10)
video_control_pub = rospy.Publisher("/pepper_video_control", String, queue_size=10)
shutdown_publisher = rospy.Publisher("/controller_shutdown", Bool, queue_size=10)

rospy.Subscriber("pepper_state", String, callback_state)


def getkey():
    global apikey
    if not apikey:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        key_file = os.path.join(base_dir, "chatGPT.key")
        if not os.path.exists(key_file):
            raise FileNotFoundError(f"API key file not found at {key_file}")
        with open(key_file, 'r') as keyfile:
            apikey = keyfile.read().strip()
    return apikey

client = openai.OpenAI(api_key=getkey())

def send_to_pepper(text):
    """
    Sends GPT-generated text to Pepper via ROS topic.
    """
    rospy.loginfo("Sending to Pepper: {}".format(text))
    speech_publisher.publish(text)
    global pepper_state
    pepper_state = "speaking"

def send_to_pepper_dispay_only(text):
    """
    Sends GPT-generated text to Pepper via ROS topic.
    """
    rospy.loginfo("Sending to Pepper: {}".format(text))
    display_publisher.publish(text)

def send_exercise_to_pepper(text):
    """
    Sends GPT-generated text to Pepper via ROS topic.
    """
    rospy.loginfo("Sending exercise Pepper: {}".format(text))
    exercise_publisher.publish(String(text))
    rospy.sleep(1)


def parse_robot_response(response):
    """
    Parse the robot response string into a tuple of (spoken_response, ready_to_exercise).

    Args:
        response (str): Robot's response string in the format '{"spoken_phrase", boolean}'.

    Returns:
        tuple: (spoken_response (str), ready_to_exercise (bool)).
               If parsing fails, returns (response (str), False).
    """
    # Regular expression to match the structure '{Spoken_response, Boolean}'
    match = re.match(r'^\{(.+?),\s*(true|false)\}$', response, re.IGNORECASE)
    if match:
        spoken_response, boolean_str = match.groups()
        spoken_response = spoken_response.strip().strip('"')  # Remove extra spaces and quotes
        ready_to_exercise = boolean_str.strip().lower() == 'true'  # Convert to boolean
        return spoken_response, ready_to_exercise

    # If parsing fails, return the raw response and False
    return response.strip(), False


async def generate_conversational_phrase(messages, csv_history_file):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=100,
            temperature=0.7,
            n=1
        )
        conversational_phrase = response.choices[0].message.content.strip()
        log_conversation("Robot", conversational_phrase, csv_file=csv_history_file)
        print("Robot:", conversational_phrase)
        return conversational_phrase
    except Exception as e:
        print(f"Error: {e}")
        return None


async def listen_for_wake_word(wake_word="hello", timeout=20):
    """
    Uses AWS Transcribe to listen for a wake word in real-time.    Args:
        wake_word (str): The phrase to trigger the system.
        timeout (int): Time in seconds before the script shuts down if no speech is detected.
    """
    print("Listening for wake word...")
    last_detection_time = time.time()  # Start tracking time    
    while True:
        # Run transcription in the background
        transcription_task = asyncio.create_task(start_transcription())        
        while not transcription_task.done():
            await asyncio.sleep(1)  # Non-blocking wait            # Check for timeout
            if time.time() - last_detection_time > timeout:
                print("No speech detected for 3 minutes. Shutting down...")
                sys.exit(0)  # Exit the script        # Get transcribed text once available
        transcribed_text = transcription_task.result()        
        if transcribed_text:
            print(transcribed_text)
            last_detection_time = time.time()  # Reset timeout            # Normalize and check if the wake word is present
            normalized_text = transcribed_text.lower().strip()
            if wake_word in normalized_text:
                print("Wake word detected!")
                return  # Exit the function and continue execution
        
def initialize_csv(conv_CSV_filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    conversational_CSV_filepath = os.path.join(base_dir,"conversation_files", conv_CSV_filename)
    if not os.path.isfile(conversational_CSV_filepath):
        log_conversation("System", "Conversation log initialized", csv_file=conv_CSV_filename)

def get_prompt(prompt_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_template_file = os.path.join(base_dir,"prompts",prompt_name)
    prompt=read_prompt_file(prompt_template_file)
    return prompt

def read_prompt_file(prompt_file):
    with open(prompt_file, 'r') as file:
        prompt_template = file.read()
    return prompt_template


async def exercise_session(messages, exercise_list, csv_history_file):
    current_set = 0
        
    EST = timezone(timedelta(hours=-5))  # Define the EST timezone
    global pepper_state

    while current_set < 4:  # 4 sets in each round
        #sp.text_to_speech(f"Let's do some {exercise_list[current_set]}.")
       
        inittime = datetime.now(EST)
        if current_set == 0:
            pepper_speech=f"I'm super excited to exercise with you. Let's do some {exercise_list[current_set]}. Do you have anything fun planned for the day? "
            send_to_pepper(pepper_speech)
            last_speaker="robot"
        else:
            pepper_speech=f"Let's do some {exercise_list[current_set]}."
            send_to_pepper_dispay_only(pepper_speech)
        
        
        messages.append({"role": "system", "content": pepper_speech})
        send_exercise_to_pepper(exercise_list[current_set])
        # Exercise phase (20 seconds)
        while (datetime.now(EST) - inittime).total_seconds() < 40:
            
            
           
            # print(f"Pepper state = {pepper_state}")
            if last_speaker == "robot" :
                try:
                    # Wait for user response
                    print("Waiting for user response...")
                    user_message = await asyncio.wait_for(start_transcription(), timeout=50)
                    log_conversation("User", user_message, csv_file=csv_history_file)
                    print("You:", user_message)
                    if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                        #sp.text_to_speech("Ending session.")
                        robot_response="Thank you for exercising with me."
                        send_to_pepper(robot_response)
                        send_exercise_to_pepper("rest")
                        log_conversation("Robot", robot_response, csv_file=csv_history_file)
                        print("Ending session.")
                        shutdown_publisher.publish(Bool(data=True))
                        return  # Exit early if the user ends the session

                    # Update last speaker and append the message
                    last_speaker = "user"
                    messages.append({"role": "user", "content": user_message})
                except asyncio.TimeoutError:
                    # Handle timeout case
                    print("Timeout: No user response detected within 20 seconds.")
                    last_speaker == "robot"

            elif last_speaker == "user":
                # Generate and speak robot response
                conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)
            
                #sp.text_to_speech(conversational_phrase)
                send_to_pepper(conversational_phrase)
                messages.append({"role": "assistant", "content": conversational_phrase})
                log_conversation("Robot", conversational_phrase, csv_history_file)

                # Update last speaker
                last_speaker = "robot"

        # End of the set
        #sp.text_to_speech("Done with the set.")
        send_to_pepper_dispay_only("Done with the set.")
        log_conversation("Robot", "Done with the set.", csv_history_file)
        send_exercise_to_pepper("rest")
        messages.append({"role": "system", "content": "Done with the set."})
        current_set += 1

        # Rest phase (40 seconds)
        if current_set < 4:
            #sp.text_to_speech("Take a rest for 40 seconds.")
            rest_mesaage="Let's take a rest for 40 seconds."
            messages.append({"role": "system", "content": rest_mesaage})
            send_to_pepper_dispay_only(rest_mesaage)    
            log_conversation("Robot","Take a rest for 40 seconds.", csv_history_file)
            send_exercise_to_pepper("rest")
            rest_start_time = datetime.now(EST)
            while (datetime.now(EST) - rest_start_time).total_seconds() < 10:
                # print(f"Pepper state = {pepper_state}")
                if last_speaker == "robot" and pepper_state == "listening":
                    try:
                        # Wait for user response
                        # user_message = await start_transcription()
                        print("Waiting for user response...")
                        user_message = await asyncio.wait_for(start_transcription(), timeout=50)
                        log_conversation("User", user_message, csv_file=csv_history_file)
                        print("You:", user_message)
                        
                        if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                            #sp.text_to_speech("Ending session.")
                            robot_response="Thank you for exercising with me."
                            send_to_pepper(robot_response)
                            send_exercise_to_pepper("rest")
                            log_conversation("Robot", robot_response, csv_file=csv_history_file)
                            print("Ending session.")
                            shutdown_publisher.publish(Bool(data=True))
                            return  # Exit early if the user ends the session

                        # Update last speaker and append the message
                        last_speaker = "user"
                        messages.append({"role": "user", "content": user_message})
                    except asyncio.TimeoutError:
                        # Handle timeout case
                        print("Timeout: No user response detected within 20 seconds.")
                        last_speaker == "robot"

                elif last_speaker == "user":
                    # Generate and speak robot response
                    conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)
                    
                    #sp.text_to_speech(conversational_phrase)
                    send_to_pepper(conversational_phrase)
                    messages.append({"role": "assistant", "content": conversational_phrase})
                    log_conversation("Robot",conversational_phrase, csv_file=csv_history_file)
                    
                    # Update last speaker
                    last_speaker = "robot"
        if current_set==4:
    #sp.text_to_speech("Great job completing this round!")
    
            send_to_pepper("Great job completing this round!")
            send_exercise_to_pepper("rest")

            messages.append({"role": "system", "content": "Great job completing this round!"})
            log_conversation("Robot","Great job completing this round!", csv_file=csv_history_file)
            shutdown_publisher.publish(Bool(data=True))
            break
    #sp.text_to_speech("Great job completing this round!")
    
    # send_to_pepper("Great job completing this round!")
    # send_exercise_to_pepper("rest")

    # messages.append({"role": "system", "content": "Great job completing this round!"})
    # log_conversation("Robot","Great job completing this round!", csv_file=csv_history_file)
                
  
  
async def main():
    participant_number = 0
    week_number=0

    csv_filename = f"participant_{participant_number}_week_{week_number}.csv"

    #initializing the CSV files 
    base_dir = os.path.dirname(os.path.abspath(__file__))
    initialize_csv(csv_filename)
    csv_history_file = os.path.join(base_dir, "conversation_files",csv_filename)
    
    if week_number == 0:
        conversational_prompt = "conversational_prompt_0.txt"
    else:
        conversational_prompt=f"conversational_prompt_{participant_number}_week_{week_number}.txt"

    
    conversational_prompt=get_prompt(conversational_prompt)

    conversational_messages = [{"role": "system", "content": conversational_prompt}]



    video_control_pub.publish(f"start recording;participant_{participant_number};week_{week_number};exercise")


    
    # Wake word detection
    ready_statement= "When you are ready to exercise, please say 'ready'."
    send_to_pepper_dispay_only(ready_statement)
    await listen_for_wake_word(wake_word="ready")

  
    print("Starting the intro session...")
    #intro_messages=await intro_session(messages, csv_history_file)
    
    print("Starting the exercise session...")
    exercise_list = ["bicep curls", "bicep curls", "lateral raises", "lateral raises"]
    await exercise_session(conversational_messages, exercise_list, csv_history_file)
    video_control_pub.publish("stop_video")

if __name__ == "__main__":
    asyncio.run(main())
