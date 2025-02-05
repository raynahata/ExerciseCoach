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
import time 
import talker
import rospy
from std_msgs.msg import String

apikey = None
access_key="ErK9WB5nNekaAlns1cldvwAU8rQSB8JPkF1QkhNfwO9vNA5FS7ihmA=="

rospy.init_node("robot_speech_publisher", anonymous=True)
speech_publisher = rospy.Publisher("/gpt_speech", String, queue_size=10)

def send_to_pepper(text):
    """
    Sends GPT-generated text to Pepper via ROS topic.
    """
    rospy.loginfo("Sending to Pepper: {}".format(text))
    speech_publisher.publish(text)
    
def getkey():
    global apikey
    if not apikey:
        # Dynamically get the directory of the current script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Construct the path to the key file relative to the script's location
        key_file = os.path.join(base_dir, "chatGPT.key")
        
        if not os.path.exists(key_file):
            raise FileNotFoundError(f"API key file not found at {key_file}")
        
        with open(key_file, 'r') as keyfile:
            apikey = keyfile.read().strip()  # Remove any trailing newline or whitespace
    return apikey

# Configure OpenAI client with key only
client = openai.OpenAI(
    api_key=getkey()
)


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
    
async def listen_for_wake_word():
    # Initialize PyPorcupine with a built-in keyword (e.g., "porcupine")
    # Get the base directory of the script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the relative path to the keyword file
    keyword_file = os.path.join(base_dir, "Hello-Pepper_en_linux_v3_0_0.ppn")
    porcupine = pvporcupine.create(
        access_key=access_key,
        keyword_paths=[keyword_file]  # Use the dynamically constructed path
    )
    
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    print("Listening for wake word...")
    while True:
        pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = [int.from_bytes(pcm[i:i+2], byteorder="little", signed=True) for i in range(0, len(pcm), 2)]
        
        keyword_index = porcupine.process(pcm)
        if keyword_index >= 0:
            print("Wake word detected!")
            audio_stream.close()
            porcupine.delete()
            return  # Exit the loop and proceed




async def main():
    # Dynamically construct paths based on the script's location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_template_file = os.path.join(base_dir, "prompt")
    csv_history_file = os.path.join(base_dir, "conversation_history.csv")

    # Initialize conversation log if not present
    if not os.path.isfile(csv_history_file):
        log_conversation("System", "Conversation log initialized", csv_file=csv_history_file)

    # Read prompt and data for initial system message
    with open(prompt_template_file, 'r') as file:
        prompt_template = file.read()

    #wake word
    initial_prompt = prompt_template
    messages = [{"role": "system", "content": initial_prompt}]
    done_chat = False
    await listen_for_wake_word() 

    # ros talker
    #talker_text, talker_state, rate = talker.talker_init()

    # Generate and print the initial response before waiting for user transcription
    print("Generating initial response...")
    initial_response = await generate_conversational_phrase(messages, csv_history_file)  #replace this with robot speech to text when transferring to robot
    
    # sp.text_to_speech(initial_response) 
    #talker.talker(initial_response, talker_state, talker_text, rate)
    send_to_pepper(initial_response)

   

    if initial_response:
        messages.append({"role": "assistant", "content": initial_response})
    while not done_chat:
    
        print("Waiting for user response...")
        user_response_start_time = time.time()  # Timer for when user input process starts
        
        try:
            # Start transcription
            user_message = await start_transcription()
            user_response_end_time = time.time()  # Timer for when user input finishes

            log_conversation("User", user_message, csv_file=csv_history_file)
            print("You:", user_message)
            
            if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                done_chat = True
                print("Ending conversation.")
                break

            messages.append({"role": "user", "content": user_message})
            
            # Generate robot's response
            print("Generating robot response...")
            
            conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)
            robot_response_start_time = time.time()

            if conversational_phrase:
                # sp.text_to_speech(conversational_phrase)
                #talker.talker(conversational_phrase, talker_state, talker_text, rate)
                send_to_pepper(conversational_phrase)

                
                # Log time intervals
                # print("Time from user speech start to robot response start:", robot_response_start_time - user_response_start_time)
                # print("Time from user speech end to robot response start:", robot_response_start_time - user_response_end_time)
                # print("Time for STT to complete:",user_response_end_time - user_response_start_time)
                
                messages.append({"role": "assistant", "content": conversational_phrase})
        
        except Exception as e:
            print(f"Error during user response or robot generation: {e}")

    

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())


#TODO: add the participant csv change
