import openai
import os
import json
from conv_logger import log_conversation
from AWS_STT import start_transcription


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

PARTICIPANT_ID = '1'

# Function to generate responses

def generate_conversational_phrase(messages, csv_history_file):
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
        print("Total Tokens:", response.usage.total_tokens)
        return conversational_phrase
    except Exception as e:
        print(f"Error: {e}")
        return None

# File paths
prompt_template_file = '/Users/raynahata/Desktop/Github/ExerciseCoach/prompt'
#data_file = '/Users/raynahata/Desktop/Github/TTRProject/occurances'
csv_history_file = '/Users/raynahata/Desktop/Github/ExerciseCoach/conversation_history.csv'

# Initialize conversation log if not present
if not os.path.isfile(csv_history_file):
    log_conversation("System", "Conversation log initialized", csv_file=csv_history_file)

# Read prompt and data for initial system message
with open(prompt_template_file, 'r') as file:
    prompt_template = file.read()

#data_file about the person
# with open(data_file, 'r') as file:
#     data = json.load(file)

#initial_prompt = prompt_template.format(**data)
initial_prompt = prompt_template

messages = [{"role": "system", "content": initial_prompt}]

done_chat = False

while not done_chat:
    conversational_phrase = generate_conversational_phrase(messages, csv_history_file)
    
    if conversational_phrase:
        print("Robot:", conversational_phrase)
        messages.append({"role": "assistant", "content": conversational_phrase})

    
    user_message = input("You: ").strip() #this for using terminal
    log_conversation("User", user_message, csv_file=csv_history_file)

    if user_message.lower() == "bye":
        done_chat = True
        print("Ending conversation.")
    else:
        messages.append({"role": "user", "content": user_message})