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


apikey = None
access_key="ErK9WB5nNekaAlns1cldvwAU8rQSB8JPkF1QkhNfwO9vNA5FS7ihmA=="

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
        #print("Robot:", conversational_phrase)
        return conversational_phrase
    except Exception as e:
        print(f"Error: {e}")
        return None
    
async def listen_for_wake_word():
    # Initialize PyPorcupine with a built-in keyword (e.g., "porcupine")
    # Get the base directory of the script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the relative path to the keyword file
    keyword_file = os.path.join(base_dir, "hello-pepper_en_mac_v3_0_0.ppn")
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

def read_prompt_file(prompt_file):
    with open(prompt_file, 'r') as file:
        prompt_template = file.read()
    return prompt_template

#gets the prompt file and reads and returns it 
def get_prompt(base_dir,prompt_name):
    prompt_template_file = os.path.join(base_dir,prompt_name)
    prompt=read_prompt_file(prompt_template_file)
    return prompt

#gets the base directory 
def get_dir_param():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return base_dir 


def initialize_csv(base_dir,conv_CSV_filename):
    conversational_CSV_filepath = os.path.join(base_dir, conv_CSV_filename)
    if not os.path.isfile(conversational_CSV_filepath):
        log_conversation("System", "Conversation log initialized", csv_file=conv_CSV_filename)


#pass in the prompt for the initial response
async def inital_robot_response(prompt_filename,conv_csv_filename):
    print("Generating initial robot response...")
    base_dir = get_dir_param()
    initial_prompt=get_prompt(base_dir,prompt_filename)
    messages = [{"role": "system", "content": initial_prompt}]
    initial_response = await generate_conversational_phrase(messages, conv_csv_filename) 
    print("Robot:",initial_response)
    return initial_response
    

#gets the prompt that it wants to use 
async def robot_response(messages,csv_history_file):
    print("Generating robot response...")  
    conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)
    print("Robot:",conversational_phrase)
    return conversational_phrase
   

async def main():
    base_dir=get_dir_param()
    print("Base directory:",base_dir)
    initialize_csv(base_dir,"conversation_history.csv")
    done_chat=False
    await listen_for_wake_word()
    initial_response = await inital_robot_response("prompt","conversation_history.csv")
    sp.text_to_speech(initial_response)
    messages=[{"role":"system","content":initial_response}]
    while not done_chat:
        print("Waiting for user response...")
        user_response_start_time=time.time()
        try:
            user_message=await start_transcription()
            user_response_end_time=time.time()
            log_conversation("User",user_message,csv_file="conversation_history.csv")
            print("You:",user_message)
            if user_message.lower().replace(" ","").strip(string.punctuation)=="bye":
                done_chat=True
                print("Ending conversation.")
                break
            messages.append({"role":"user","content":user_message})
            conversational_phrase=await robot_response(messages,"conversation_history.csv")
            robot_response_start_time=time.time()
            if conversational_phrase:
                sp.text_to_speech(conversational_phrase)
                print("Time from user speech start to robot response start:",robot_response_start_time-user_response_start_time)
                print("Time from user speech end to robot response start:",robot_response_start_time-user_response_end_time)
                print("Time for STT to complete:",user_response_end_time-user_response_start_time)
                messages.append({"role":"assistant","content":conversational_phrase})
        except Exception as e:
            print(f"Error during user response or robot generation: {e}")
  
   
#Run the event loop
if __name__ == "__main__":
    asyncio.run(main())


#TODO: add the participant csv change
