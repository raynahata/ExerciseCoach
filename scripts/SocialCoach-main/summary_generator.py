import openai
import pandas as pd
import os
import yaml


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    config_path = os.path.join(BASE_DIR, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def get_key():
    key_file = os.path.join(BASE_DIR, "chatGPT.key")

    if not os.path.exists(key_file):
        raise FileNotFoundError(f"API key file not found at {key_file}")

    with open(key_file, 'r') as keyfile:
        return keyfile.read().strip()


def load_conversation(participant, week, csv_filepath=None):
    csv_filename = f"participant_{participant}_week_{week}.csv"
    if csv_filepath is None:
        csv_filepath = os.path.join(BASE_DIR, "conversation_files", csv_filename)

    try:
        df = pd.read_csv(csv_filepath, encoding="utf-8", names=["Timestamp", "Speaker", "Message"], skiprows=1)
        df = df[["Speaker", "Message"]].dropna()
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


def load_prompt(prompt_filename):
    prompt_filepath = os.path.join(BASE_DIR, "prompts", prompt_filename)

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


def merge_prompt_conversation(prompt_template, conversation_text):
    return f"{prompt_template}\n\nConversation:\n{conversation_text}"


def generate_summary(final_prompt, model="gpt-4o", max_tokens=250):
    api_key = get_key()
    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI that summarizes conversations into concise paragraphs."},
                {"role": "user", "content": final_prompt}
            ],
            max_tokens=max_tokens
        )

        if response and hasattr(response, "choices") and response.choices:
            summary = response.choices[0].message.content.strip()
            return summary

        print(f"Error: {model} did not return a valid summary.")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None


def save_summary(participant, week, summary):
    summaries_folder = os.path.join(BASE_DIR, "summaries")
    os.makedirs(summaries_folder, exist_ok=True)

    summary_filename = f"summary_p{participant}_week{week}.txt"
    summary_filepath = os.path.join(summaries_folder, summary_filename)

    try:
        with open(summary_filepath, "w", encoding="utf-8") as file:
            file.write(summary)
        print(f"Summary saved to {summary_filepath}")
        return summary_filepath
    except Exception as e:
        print(f"Error saving summary: {e}")
        return None


def generate_summary_for_session(
    participant,
    week,
    csv_filepath=None,
    prompt_filename="summaryPrompt.txt",
    model="gpt-4o",
    max_tokens=250
):
    conversation_text = load_conversation(participant, week, csv_filepath=csv_filepath)
    prompt_template = load_prompt(prompt_filename)

    if not conversation_text or not prompt_template:
        return None

    final_prompt = merge_prompt_conversation(prompt_template, conversation_text)
    summary = generate_summary(final_prompt, model=model, max_tokens=max_tokens)
    if not summary:
        print("Error: No summary was generated.")
        return None

    return save_summary(participant, week, summary)


def main():
    params = load_config()
    participant = int(params.get("participant_number", 0))
    week = int(params.get("week_number", 0))
    prompt_filename = params.get("summary_prompt_file", "summaryPrompt.txt")
    model = params.get("summary_model", "gpt-4o")
    max_tokens = int(params.get("summary_max_tokens", 250))

    generate_summary_for_session(
        participant,
        week,
        prompt_filename=prompt_filename,
        model=model,
        max_tokens=max_tokens
    )

if __name__ == "__main__":
    main()
