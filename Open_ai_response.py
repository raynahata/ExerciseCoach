import openai
import os
import asyncio
from AWS_STT import start_transcription  # Import the transcription function
from conv_logger import log_conversation
import string

apikey = None

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

async def main():
    prompt_template_file = '/Users/raynahata/Desktop/Github/ExerciseCoach/prompt'
    csv_history_file = '/Users/raynahata/Desktop/Github/ExerciseCoach/conversation_history.csv'

    # Initialize conversation log if not present
    if not os.path.isfile(csv_history_file):
        log_conversation("System", "Conversation log initialized", csv_file=csv_history_file)

    # Read prompt and data for initial system message
    with open(prompt_template_file, 'r') as file:
        prompt_template = file.read()

    initial_prompt = prompt_template
    messages = [{"role": "system", "content": initial_prompt}]
    done_chat = False

    # Generate and print the initial response before waiting for user transcription
    print("Generating initial response...")
    initial_response = await generate_conversational_phrase(messages, csv_history_file)
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
            if conversational_phrase:
                messages.append({"role": "assistant", "content": conversational_phrase})

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())

