# ExerciseCoach

ExerciseCoach is a speech-driven interactive system for social interaction using Pepper, ROS Noetic, and AWS services for voice-based interactions.

## Base Code & Tutorials
- **STT Base Code:** [AWS Boto3 Text Analytics for PDF - Amazon Textract](https://github.com/RekhuGopal/PythonHacks/blob/main/AWSBoto3Hacks/AWSboto3TextAnalytics-PDF-AmazonTextract.py)
- **Tutorial:** [YouTube Video](https://www.youtube.com/watch?v=_q5vBvTNDEA)

---

## Setup Instructions

### 1. Install ROS Noetic
ROS Noetic is required to bridge Python 2 and Python 3. Follow the installation guide:
[ROS Noetic Installation](https://wiki.ros.org/noetic/Installation)

### 2. Install Python2 and Python3
- **naoqi SDK** depends on **Python2**.
- **Python3** is required for OpenAI API calls.

### 3. Configure AWS CLI
Follow the official guide to configure AWS CLI:
[Getting Started with AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html)

### 4. Install Dependencies
Run the following command to install required Python packages:
```sh
python3 -m pip install pynput asyncio sounddevice pvporcupine pyaudio gtts openai amazon_transcribe
```

### 5. Configure naoqi SDK for Pepper
1. Download the naoqi SDK:  
   [naoqi SDK Installation Guide](http://doc.aldebaran.com/1-14/dev/python/install_guide.html#python-install-guide)
2. Unzip the SDK file:
   ```sh
   unzip /path/to/python-sdk.zip
   ```

---

## Running the Project
You need **three terminal windows** to run the entire system:

### **Terminal 1: Start ROS Core**
```sh
roscore
```

### **Terminal 2: Run Pepper Controller (Python 2)**
1. Set the environment variable for naoqi SDK:
   ```sh
   export PYTHONPATH=${PYTHONPATH}:/path/to/python-sdk
   ```
2. Run the Pepper controller:
   ```sh
   python2 pepper_controller.py
   ```

### **Terminal 3: Run Pepper Social Section (Python 3)**
```sh
python3 Pepper_social_section.py
```

---

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

# Branches 
The main branch can be run on a standard Mac and is not ROS integrated.  
The TBD-LAT is ROS integrated. 

