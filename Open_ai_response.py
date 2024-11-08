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


apikey = None
access_key="ErK9WB5nNekaAlns1cldvwAU8rQSB8JPkF1QkhNfwO9vNA5FS7ihmA=="

def getkey():
    global apikey
    if not apikey:
        filename = '/Users/raynahata/Desktop/Github/ExerciseCoach/chatGPT.key'
        with open(filename, 'r') as keyfile:
            apikey = keyfile.read().strip('/n')
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
    porcupine = pvporcupine.create(
        access_key=access_key,
        keyword_paths=["/Users/raynahata/Desktop/Github/ExerciseCoach/hello-pepper_en_mac_v3_0_0.ppn"]  # Replace with your desired keyword
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
    prompt_template_file = '/Users/raynahata/Desktop/Github/ExerciseCoach/prompt'
    csv_history_file = '/Users/raynahata/Desktop/Github/ExerciseCoach/conversation_history.csv'

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
    # Generate and print the initial response before waiting for user transcription
    print("Generating initial response...")
    initial_response = await generate_conversational_phrase(messages, csv_history_file)  #replace this with robot speech to text when transferring to robot
    print("Begin speaking")
    #logger.info('Begin speaking,{}'.format(message))
    sp.text_to_speech(initial_response)
    #logger.info('End speaking')
    print("End speaking")
    if initial_response:
        messages.append({"role": "assistant", "content": initial_response})

    while not done_chat:
        # Print a prompt to indicate waiting for user input
        print("Waiting for user response...")
        
        # Start the transcription only when needed
        # user_message = await start_transcription()
        user_message = await start_transcription()
        #print("Received transcription:", user_message)
        #user_message=start_transcription() #this for transcition
        #user_message = input("You: ").strip() #this for using terminal

        # Log and process the user response
        log_conversation("User", user_message, csv_file=csv_history_file)
        print("You:", user_message)

        if user_message.lower().replace(" ", "").strip(string.punctuation) == "bye":
            done_chat = True
            print("Ending conversation.")
        else:
            messages.append({"role": "user", "content": user_message})

            # Generate the next OpenAI response
            conversational_phrase = await generate_conversational_phrase(messages, csv_history_file)
            sp.text_to_speech(conversational_phrase) #replace this with robot speech to text when transferring to robot
            if conversational_phrase:
                messages.append({"role": "assistant", "content": conversational_phrase})

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())


#TODO: add the participant csv change
