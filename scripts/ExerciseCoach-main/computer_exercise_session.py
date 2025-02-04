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

import time 

# Initialize OpenAI client
apikey = None
access_key="ErK9WB5nNekaAlns1cldvwAU8rQSB8JPkF1QkhNfwO9vNA5FS7ihmA=="

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
        
def initialize_csv(conv_CSV_filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    conversational_CSV_filepath = os.path.join(base_dir, conv_CSV_filename)
    if not os.path.isfile(conversational_CSV_filepath):
        log_conversation("System", "Conversation log initialized", csv_file=conv_CSV_filename)

def get_prompt(prompt_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_template_file = os.path.join(base_dir,prompt_name)
    prompt=read_prompt_file(prompt_template_file)
    return prompt

def read_prompt_file(prompt_file):
    with open(prompt_file, 'r') as file:
        prompt_template = file.read()
    return prompt_template

async def exercise_session(messages, exercise_list, csv_history_file):
    current_set = 0
    sp.text_to_speech("Starting the social session.")
    last_speaker = "robot"  # Initialize the last speaker as the robot
    EST = timezone(timedelta(hours=-5))  # Define the EST timezone

    while current_set < 4:  # 4 sets in each round
        sp.text_to_speech(f"Let's do some {exercise_list[current_set]}.")
        messages.append({"role": "system", "content": f"Let's do some {exercise_list[current_set]}."})
        inittime = datetime.now(EST)

        # Exercise phase (20 seconds)
        while (datetime.now(EST) - inittime).total_seconds() < 20:
            if last_speaker == "robot":
                # Wait for user response
                print("Waiting for user response...")
                user_message = await start_transcription()
                log_conversation("User", user_message, csv_file=csv_history_file)
                print("You:", user_message)
                if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                    sp.text_to_speech("Ending session.")
                    print("Ending session.")
                    return  # Exit early if the user ends the session

                # Update last speaker and append the message
                last_speaker = "user"
                messages.append({"role": "user", "content": user_message})

            elif last_speaker == "user":
                # Generate and speak robot response
                conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)
                sp.text_to_speech(conversational_phrase)
                messages.append({"role": "assistant", "content": conversational_phrase})

                # Update last speaker
                last_speaker = "robot"

        # End of the set
        sp.text_to_speech("Done with the set.")
        messages.append({"role": "system", "content": "Done with the set."})
        current_set += 1

        # Rest phase (40 seconds)
        if current_set < 4:
            sp.text_to_speech("Take a rest for 40 seconds.")
            rest_start_time = datetime.now(EST)
            while (datetime.now(EST) - rest_start_time).total_seconds() < 40:
                if last_speaker == "robot":
                    # Wait for user response
                    print("Waiting for user response...")
                    user_message = await start_transcription()
                    log_conversation("User", user_message, csv_file=csv_history_file)
                    print("You:", user_message)
                    if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
                        sp.text_to_speech("Ending session.")
                        print("Ending session.")
                        return  # Exit early if the user ends the session

                    # Update last speaker and append the message
                    last_speaker = "user"
                    messages.append({"role": "user", "content": user_message})

                elif last_speaker == "user":
                    # Generate and speak robot response
                    conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)
                    sp.text_to_speech(conversational_phrase)
                    messages.append({"role": "assistant", "content": conversational_phrase})

                    # Update last speaker
                    last_speaker = "robot"

    sp.text_to_speech("Great job completing this round!")
    messages.append({"role": "system", "content": "Great job completing this round!"})

async def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_history_file = os.path.join(base_dir, "conversation_history.csv")
    initial_prompt=get_prompt("prompt")
    messages = [{"role": "system", "content": initial_prompt}]


    # Wake word detection
    await listen_for_wake_word()

    # Generate initial response
    # print("Generating initial response...")
    # initial_response = await generate_conversational_phrase(messages, csv_history_file) 
    # sp.text_to_speech(initial_response)
    
    # if initial_response:
    #     messages.append({"role": "assistant", "content": initial_response})

    # Exercise interaction
    exercise_list = ["bicep curls", "bicep curls", "lateral raises", "lateral raises"]
    await exercise_session(messages, exercise_list, csv_history_file)

if __name__ == "__main__":
    asyncio.run(main())