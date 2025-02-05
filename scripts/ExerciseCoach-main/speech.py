from gtts import gTTS
import os

from io import BytesIO


# Dynamically construct the folder path based on the script's location

def text_to_speech(text):
    text=str(text)
    
    text_quote = text.replace("'","")
    text_quote = text_quote.replace("]", "")
    text_quote = text_quote.replace("/", "")

    # Initialize gTTS with the text to convert
    speech = gTTS(text_quote, lang='en')
   

    # Save the audio file to a temporary file
    speech_file = 'speech.mp3'
    speech.save(speech_file)

    # Play the audio file
    os.system('afplay ' + speech_file)


# def main(): #tester main function 
#     text=im.INTAKE_MESSAGES["Introduction"]["Greeting"]
#     text_to_speech(text)



