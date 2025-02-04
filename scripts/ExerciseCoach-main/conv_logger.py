import logging
import csv
from datetime import datetime
import os


# Set up the logger for plain text logging (optional, if you still want the .txt log)
logging.basicConfig(filename="conversation_log.txt", 
                    level=logging.INFO, 
                    format="%(asctime)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

def log_conversation(speaker, message, csv_file="conversation_history.csv"):
    """
    Logs the conversation with date, time, speaker, and message.

    Parameters:
    - speaker (str): Who said it (e.g., 'User', 'Robot')
    - message (str): What they said
    - csv_file (str): Path to the CSV file for logging conversation history.
    """
    # Log to the text file
    log_message = f"{speaker}: {message}"
    logging.info(log_message)
    
    # Check if the CSV file exists, and if not, create it with headers
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        # Write header if file is new
        if not file_exists:
            writer.writerow(['role', 'content', 'timestamp'])
        
        # Write the conversation line with timestamp
        writer.writerow([ datetime.now().strftime("%Y-%m-%d %H:%M:%S"),speaker, message])

def load_conversation_history(csv_file="conversation_history.csv"):
    """
    Load conversation history from a CSV file and format it as a list of messages.

    Parameters:
    - csv_file (str): Path to the CSV file with conversation history.

    Returns:
    - list of dicts: Each dict represents a message with 'role' and 'content'.
    """
    messages = []
    try:
        with open(csv_file, newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Ensure 'role' and 'content' are in each row
                if 'role' in row and 'content' in row:
                    messages.append({"role": row['role'], "content": row['content']})
                else:
                    print("Warning: Row missing 'role' or 'content' field.")
    except FileNotFoundError:
        print(f"Warning: CSV file '{csv_file}' not found. Starting with an empty history.")
    return messages
