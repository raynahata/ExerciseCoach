# ExerciseCoach

The STT base code is from: https://github.com/RekhuGopal/PythonHacks/blob/main/AWSBoto3Hacks/AWSboto3TextAnalytics-PDF-AmazonTextract.py

Tutorial linked to the base code: https://www.youtube.com/watch?v=_q5vBvTNDEA 

## Setup

### Configuring AWS CLI 
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html 

### Dependencies (there may be more than what is listed on here) 
pip install pynput asyncio sounddevice time pyporcupine pyaudio gtts openai


## File Information 
### AWS_STT.py
This is the current working file. This code will quit the transcription each time. 

### aws_backup.py 
This file will continually run the transcription. If you use this with the Open_AI file, it will not work. The continual listening somehow keeps the Open_AI file from moving onto the next line of code. 

### Open_ai_response.py
This is the current working file. **Run this file to do the full loop. **
NOTE: You will need your own Open AI key. That can be modified at the getKey() function at the top. 
Wake word: Hello Pepper. 

### Open_ai_backup.py 
This will run a chatbot-like style. You can converse by typing the responses into the terminal. This file will not communicate with AWS STT.

## Wake word training 
1) Install pyporcupine
2) Create a porcupine account at https://picovoice.ai/docs/quick-start/porcupine-python/
3) Create a wake word (NOTE: The free versoin only lets you train for three so choose wisely)
4) Download the wake word file and add it to the main file 
