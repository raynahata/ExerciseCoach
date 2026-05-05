#before the study 
export PYTHONPATH=${PYTHONPATH}:/home/raynahata/ExerciseCoach/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages
python2 reset_page.py 

#To run the Study 

##Terminal one 
rosecore 

##Terminal two 

export PYTHONPATH=${PYTHONPATH}:/home/raynahata/ExerciseCoach/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages

cd ExerciseCoach/scripts/SocialCoach-main

python2 pepper_controller_eyes.py

##Terminal three
cd ExerciseCoach/scripts/SocialCoach-main

python pepper_intro_session.py 

python Pepper_social_session_eyes.py

# ExerciseCoach

The STT base code is from: https://github.com/RekhuGopal/PythonHacks/blob/main/AWSBoto3Hacks/AWSboto3TextAnalytics-PDF-AmazonTextract.py

Tutorial linked to the base code: https://www.youtube.com/watch?v=_q5vBvTNDEA 

## Setup

### Configuring AWS CLI 
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html 

### Dependencies (there may be more than what is listed on here) 
pip install pynput asyncio sounddevice time pyporcupine pyaudio gtts openai


## File Information 
### Open_ai_response.py
This is the current working file. **Run this file to do the full loop. **
NOTE: You will need your own Open AI key. That can be modified at the getKey() function at the top. 
Wake word: Hello Pepper.

### AWS_STT.py
This is the current working file. This code will quit the transcription each time. 

### aws_backup.py 
This file will continually run the transcription. If you use this with the Open_AI file, it will not work. The continual listening somehow keeps the Open_AI file from moving onto the next line of code. 

### Open_ai_backup.py 
This will run a chatbot-like style. You can converse by typing the responses into the terminal. This file will not communicate with AWS STT.

## Wake word training 
1) Install pyporcupine
2) Create a porcupine account at https://picovoice.ai/docs/quick-start/porcupine-python/
3) Create a wake word (NOTE: The free versoin only lets you train for three so choose wisely)
4) Download the wake word file and add it to the main file 


# Pepper Related
We are not directly ssh into Pepper. 
We need an external computer to run all of our code including ROS code, 
and use naoqi proxy for sending signal to Pepper.

Overall Structure
---
Step 1:
 - Installing naoqi SDK for python2.7 on the external computer
 https://www.aldebaran.com/en/support/nao-6/downloads-softwares
 - Extract the tar.gz file and export the package
 ```
 export PYTHONPATH=${PYTHONPATH}:/home/raynahata/exercise_bot/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages
 ```

Step 2:
 - Make sure python3 is also installed for running all previous ROS code 
 or other packages

Step 3: 
 - Starting roscore / rosmaster node

Step 4:
 - Running the listener.py by python2.7 
 - (The file is a ros suscriber node using naoqi SDK python2.7 
 and using Ros 1 Noetic)
```
python2 listener.py
```

Step 5:
 - Running the rest of the node by python3

Some others notes on using naoqi API:
---
- Using from naoqi and import ALProxy is similar to accessing a topic in ROS 
- Using the line below to subscribe to a specific topic on Pepper, where 9559 is the default port.
```
ALProxy(SOMETOPIC, IP, 9559)
```



CheckList:
---
> Finished modifying the text to speech nodes

> Successfully running ROS1 on python2 (with naoqi API) and python3

> Successfully display a website while speech to text but still looking for ways to display an html locally.

> TODO: looking up some ways to launch an html locally on Pepper (need to look into the documentation)
