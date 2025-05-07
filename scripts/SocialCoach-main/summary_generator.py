import openai
import pandas as pd
import os
import csv

# Function to retrieve the OpenAI API key from a file
def get_key():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_file = os.path.join(base_dir, "chatGPT.key")

    if not os.path.exists(key_file):
        raise FileNotFoundError(f"API key file not found at {key_file}")

    with open(key_file, 'r') as keyfile:
        return keyfile.read().strip()

# Function to load and clean conversation from a dynamically changing CSV file
def load_conversation(participant,week):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = f"participant_{participant}_week_{week}.csv"
    csv_filepath = os.path.join(base_dir, "conversation_files", csv_filename)

    try:
        # Load CSV
        df = pd.read_csv(csv_filepath, encoding="utf-8", names=["Timestamp", "Speaker", "Message"], skiprows=1)

        # Keep only the "Speaker" and "Message" columns
        df = df[["Speaker", "Message"]].dropna()

        # Convert the conversation into one long string while preserving "Robot:" and "User:"
        conversation_text = "\n".join(f"{row['Speaker']}: {row['Message']}" for _, row in df.iterrows())

        if not conversation_text.strip():
            print(f"Error: The conversation file for participant {participant} is empty or unreadable.")
            return None

        return conversation_text

    except FileNotFoundError:
        print(f"Error: The file '{csv_filepath}' was not found for participant {participant}.")
        return None
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

# Function to load the summarization prompt from a file
def load_prompt(prompt_filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_filepath = os.path.join(base_dir, "prompts", prompt_filename)

    try:
        with open(prompt_filepath, "r", encoding="utf-8") as file:
            prompt = file.read().strip()
            if not prompt:
                print("Error: The prompt file is empty.")
                return None
            return prompt
    except FileNotFoundError:
        print(f"Error: Prompt file '{prompt_filepath}' not found.")
        return None

# Function to merge the prompt template with the conversation text
def merge_prompt_conversation(prompt_template, conversation_text):
    return f"{prompt_template}\n\nConversation:\n{conversation_text}"

# Function to generate a summary using GPT-4
def generate_summary(final_prompt):
    api_key = get_key()
    openai.api_key = api_key  # Ensure API key is correctly set

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI that summarizes conversations into concise paragraphs."},
                {"role": "user", "content": final_prompt}
            ],
            max_tokens=250  # Adjust as needed
        )

        # Ensure correct response handling
        if response and hasattr(response, "choices") and response.choices:
            summary = response.choices[0].message.content.strip()
            return summary

        print("Error: GPT-4o did not return a valid summary.")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None

# Function to save the summary to a file dynamically
def save_summary(participant_ID,week, summary):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summaries_folder = os.path.join(base_dir, "summaries")

    # Ensure the "summaries" folder exists
    os.makedirs(summaries_folder, exist_ok=True)
    
    
    summary_filename = f"summary_p{participant_ID}_week{week}.txt"
    summary_filepath = os.path.join(summaries_folder, summary_filename)

    try:
        with open(summary_filepath, "w", encoding="utf-8") as file:
            file.write(summary)
        print(f"Summary saved to {summary_filepath}")
    except Exception as e:
        print(f"Error saving summary: {e}")

# Main function to execute the script
def main():
    # Set participant ID dynamically
    #week 0 if the first wek so you want to save as the week after 
    participant_ID = 3
    week = 2

    # Specify the prompt filename (static)
    prompt_filename = "summaryPrompt.txt"

    # Load conversation and prompt
    conversation_text = load_conversation(participant_ID,week)
    prompt_template = load_prompt(prompt_filename)

    if conversation_text and prompt_template:
        final_prompt = merge_prompt_conversation(prompt_template, conversation_text)  # Append conversation below prompt
        
        if final_prompt:
            summary = generate_summary(final_prompt)  # Generate summary with GPT-4o
            if summary:
                #print("\nSummary:\n", summary)
                save_summary(participant_ID,week, summary)  # Save summary dynamically
            else:
                print("Error: No summary was generated.")
        else:
            print("Error: Merging prompt and conversation failed.")

if __name__ == "__main__":
    main()