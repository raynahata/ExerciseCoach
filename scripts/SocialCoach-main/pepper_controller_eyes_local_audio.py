# This node file should be run on Python 2.7
# export PYTHONPATH=${PYTHONPATH}:/home/raynahata/ExerciseCoach/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages

# export PYTHONPATH=${PYTHONPATH}:/home/roshni/Pepper/ExerciseCoach/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages

import rospy
from naoqi import ALProxy
import math
import time
from std_msgs.msg import String
from std_msgs.msg import Bool
from sensor_msgs.msg import Image
import sys
import threading
import os
import subprocess
import atexit
from datetime import datetime
import yaml

def load_config():
    """Load shared config (participant_number, week_number, pepper_ip)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

class Pepper:
    def __init__(self):
        params = load_config()
        self.IP = params.get("pepper_ip", "127.0.0.1")
        self.participant_number = str(params.get("participant_number", 0))
        self.week_number = str(params.get("week_number", 0))
        self.tts = ALProxy("ALTextToSpeech", self.IP, 9559)
        self.motion = ALProxy("ALMotion", self.IP, 9559)
        self.posture = ALProxy("ALRobotPosture", self.IP, 9559)
        self.life = ALProxy('ALAutonomousLife', self.IP, 9559)
        self.life.setAutonomousAbilityEnabled("All", True)
        #self.life.setAutonomousAbilityEnabled("All", False)
        #self.life.stopAll()
        self.tablet = ALProxy("ALTabletService",self.IP,9559)
        self.memory = ALProxy("ALMemory", self.IP, 9559)
        self.leds = ALProxy("ALLeds", self.IP, 9559)
        self.tts.setParameter("defaultVoiceSpeed", 70)
        self.tts.setParameter("pitchShift", 1)
        
        # Initialize recording variables
        self.recording = False
        self.audio_process = None
        self.audio_file = None
        
        # Generate timestamp for synchronized recordings
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Setup directories
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.recordings_dir = os.path.join(base_dir, "recordings")
        if not os.path.exists(self.recordings_dir):
            os.makedirs(self.recordings_dir)
        
        # Start local audio recording using system commands
        self.start_system_audio_recording()
        atexit.register(self.cleanup_audio)

        self.start_rosbag_video_recording()
        atexit.register(self.stop_rosbag_video_recording)
        
    #initialize camera
        resolution = 2  # 640x480
        color_space = 11  # RGB
        fps = 5  # Frames per second
        self.video_service = ALProxy("ALVideoDevice", self.IP, 9559)
        self.subscriber_id = self.video_service.subscribeCamera("video_stream", 0, resolution, color_space, fps)

        self.exercise_running=False
        self.pepper_thinking = False

        self.state = ""
        self.current_text = ""

        # ROS Publishers and Subscribers
        rospy.init_node("pepper_controller", anonymous=True)
        self.state_pub = rospy.Publisher("pepper_state", String, queue_size=10)
        self.text_pub = rospy.Publisher("chat_text", String, queue_size=10)
        self.exercise_publisher = rospy.Publisher("/exercise_command", String, queue_size=10)
        self.tts_status_pub = rospy.Publisher('/pepper/tts_status', Bool, queue_size=1)
        rospy.Subscriber("pepper_state", String, self.callback_state)
        rospy.Subscriber("gpt_speech", String, self.gpt_callback)
        rospy.Subscriber("speech_display", String, self.display_callback)
        rospy.Subscriber("exercise_command", String, self.exercise_callback)
        
        rospy.Subscriber("controller_shutdown", Bool, self.shutdown_callback)

        self.image_publisher = rospy.Publisher("/pepper_camera/image_raw", Image, queue_size=10)

        rospy.loginfo("Subscribed to /gpt_speech")

        self.exercise_running = False  # True when an exercise is running
        self.current_exercise = None  # Stores the name of the current exercise
        self.is_resting = False  # True when Pepper is resting

        rospy.loginfo("Subscribed to /exercise_command topic.")

    def shutdown_callback(self, msg):
        rospy.loginfo("Received shutdown command: {}".format(msg.data))
        if msg.data == True:
            rospy.loginfo("Shutting down controller node and exiting...")
            rospy.signal_shutdown("Shutdown requested by social session")
            sys.exit(0)
    
    ### Helper Function: Convert Degrees to Radians ###
    def degrees_to_radians(self, angles_in_degrees):
        """
        Convert a list of angles from degrees to radians.
        Args:
            angles_in_degrees: List of angles in degrees.
        Returns:
            List of angles in radians.
        """
        return [angle * math.pi / 180.0 for angle in angles_in_degrees]

    ### Function to Move Arms ###
    def move_arm(self, side, angles, speed=0.2):
        """
        Move Pepper's arm to the specified angles.
        Args:
            side: "R" for right arm, "L" for left arm.
            angles: List of angles (in radians) for the arm's joints.
            speed: Fraction of maximum speed (0.0 to 1.0).
        """
        if side == "R":
            joint_names = ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RWristYaw"]
        elif side == "L":
            joint_names = ["LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LWristYaw"]
        else:
            rospy.logerr("Invalid side specified. Use 'R' for right arm or 'L' for left arm.")
            return

        if len(angles) != len(joint_names):
            rospy.logerr("Number of angles does not match the number of joints.")
            return

        rospy.loginfo("Moving {} arm to angles: {}".format(side, angles))
        self.motion.setAngles(joint_names, angles, speed)
        #self.motion.angleInterpolation(joint_names,angles,[speed]*len(joint_names),True)

    def exercise_callback(self, msg):
        """
        Handles incoming exercise commands.
        """
        rospy.loginfo("Received exercise command: {}".format(msg.data))
        command = msg.data.lower()

        if command == "bicep curls":
            if not self.exercise_running:
                rospy.loginfo("Starting bicep curls...")
                self.exercise_running = True
                self.is_resting = False
                self.current_exercise = "bicep curls"
                self.set_eye_color((255, 255, 255))

                threading.Thread(target=self.bicep_curls).start()
            else:
                rospy.loginfo("Bicep curls are already running.")

        elif command == "lateral raises":
            if not self.exercise_running:
                rospy.loginfo("Starting lateral raises...")
                self.exercise_running = True
                self.is_resting = False
                self.current_exercise = "lateral raises"
                self.set_eye_color((255, 255, 255))
                # self.lateral_raises()
                threading.Thread(target=self.lateral_raises).start()
            else:
                rospy.loginfo("Lateral raises are already running.")

        elif command == "rest":
            if self.exercise_running:
                rospy.loginfo("Stopping exercise and entering rest phase...")
                self.exercise_running = False
                self.current_exercise = None
                self.is_resting = True
                self.set_eye_color((0, 0, 255))
                self.stop_exercise_motion()
            else:
                rospy.loginfo("Already in rest phase.")

    def say_text(self, text):
        """
        Make Pepper say the provided text.
        """
        rospy.loginfo("Saying: {}".format(text))
        self.tts.say(text)

    def set_flag_listening(self):
        """
        Set state to 'listening' and trigger appropriate action.
        """
        self.state = "listening"
        self.state_pub.publish("listening")

    def set_flag_speaking(self):
        """
        Set state to 'speaking' and trigger appropriate action.
        """
        self.state = "speaking"
        self.state_pub.publish("speaking")
        
    def gpt_callback(self, data):
        """
        Callback for 'chat_text' topic.
        """
        rospy.loginfo("Received GPT Speech: {}".format(data.data))
        self.current_text = data.data
        self.set_flag_speaking()
        self.display_text(self.current_text)
        self.tts_status_pub.publish(True)
        rospy.loginfo("Set speaking status to true...")
        self.say_text(self.current_text)
        # self.display_text(self.current_text)
        while (self.memory.getData("ALTextToSpeech/Status"))[1] != "done":
            
            time.sleep(0.1)
        rospy.loginfo("Finished Speaking...")
        self.tts_status_pub.publish(False)
        
        self.set_flag_listening()

    def display_callback(self, data):
        """
        Callback for 'chat_text' topic.
        """
        rospy.loginfo("Received display text: {}".format(data.data))
        self.current_text = data.data
        self.display_text(self.current_text)
    
    def callback_state(self, data):
        """
        Callback for 'pepper_state' topic.
        """
        rospy.loginfo("Received state: {}".format(data.data))
        self.state = data.data

    def publish_text(self, text):
        """
        Publish text to the 'chat_text' topic.
        """
        rospy.loginfo("Publishing text: {}".format (text))
        self.text_pub.publish(text)
    
    def clear_screen(self):
        rospy.loginfo("Clearing Pepper's tablet screen.")
        js_script = """document.body.innerHTML = `<style>body{background:#f0f0f0;margin:0;}</style>`;"""
        self.tablet.executeJS(js_script)

    def display_text(self, message):
        """
        Displays animated scrolling text on Pepper's tablet using JavaScript.
        """
        rospy.loginfo("Displaying static text on tablet: {}".format(message))
        js_script = """document.body.innerHTML = `<style>body{font-family:Arial,sans-serif;text-align:center;background:#f0f0f0;display:flex;justify-content:center;align-items:center;height:100vh;width:100vw;margin:0;padding:20px;overflow:hidden;} .text{font-size:10vh;color:#333;width:90vw;height:100vh;word-wrap:break-word;overflow-wrap:break-word;display:flex;align-items:center;justify-content:center;text-align:center;white-space:normal;line-height:1.5;}</style><div class='text'>""" + message + """</div>`;"""
        self.tablet.executeJS(js_script)

    def set_eye_color(self, color):
        r, g, b = color
        hex_color = (r << 16) | (g << 8) | b  # Convert to hex format
        self.leds.fadeRGB("FaceLeds", hex_color, 1.0)

    ### Hardcoded Arm Motion: Up ###
    def stop_exercise_motion(self):
        self.motion.stopMove()
        self.motion.setStiffnesses("Body",0.0)
        
    def lateral_arm_motion_up(self):
        """
        Move both arms to the 'up' position.
        """
        # Right arm angles in degrees (arm up)
        right_arm_angles_degrees = [101.2, -89.4, 97.3, 5.8, -1.0]
        right_arm_angles_radians = self.degrees_to_radians(right_arm_angles_degrees)

        # Left arm angles in degrees (arm up)
        left_arm_angles_degrees = [101.2, 89.4, -97.3, -5.8, 1.0]
        left_arm_angles_radians = self.degrees_to_radians(left_arm_angles_degrees)

        # Move the right arm
        self.move_arm("R", right_arm_angles_radians, speed=0.2)

        # Move the left arm
        self.move_arm("L", left_arm_angles_radians, speed=0.2)

    ### Hardcoded Arm Motion: Down ###
    def lateral_arm_motion_down(self):
        """
        Move both arms to the 'down' position.
        """
        # Right arm angles in degrees (arm down)
        right_arm_angles_degrees = [101.2, -0.5, 97.3, 5.8, -1.0]
        right_arm_angles_radians = self.degrees_to_radians(right_arm_angles_degrees)

        # Left arm angles in degrees (arm down)
        left_arm_angles_degrees = [101.2, 2.3, -98, -6, 1.9]
        left_arm_angles_radians = self.degrees_to_radians(left_arm_angles_degrees)

        # Move the right arm
        self.move_arm("R", right_arm_angles_radians, speed=0.2)

        # Move the left arm
        self.move_arm("L", left_arm_angles_radians, speed=0.2)

    ### Hardcoded Arm Motion: Up ###
    def bicep_arm_motion_up(self):
        """
        Move both arms to the 'up' position.
        """
        # Right arm angles in degrees (arm up)
        right_arm_angles_degrees = [76.0,-23.0,83.0,89.0,104.5]
        right_arm_angles_radians = self.degrees_to_radians(right_arm_angles_degrees)

        # Left arm angles in degrees (arm up)
        left_arm_angles_degrees = [76.0,23.0,-83.0,-89.0,-104.5]
        left_arm_angles_radians = self.degrees_to_radians(left_arm_angles_degrees)

        # Move the right arm
        self.move_arm("R", right_arm_angles_radians, speed=0.1)

        # Move the left arm
        self.move_arm("L", left_arm_angles_radians, speed=0.1)

    ### Hardcoded Arm Motion: Down ###
    def bicep_arm_motion_down(self):
        """
        Move both arms to the 'down' position.
        """
        # Right arm angles in degrees (arm down)
        right_arm_angles_degrees = [76.0,-23.0,83.0,0.7,104.5]
        right_arm_angles_radians = self.degrees_to_radians(right_arm_angles_degrees)

        # Left arm angles in degrees (arm down)
        left_arm_angles_degrees = [76.0,23.0,-83.0,-0.7,-104.5]
        left_arm_angles_radians = self.degrees_to_radians(left_arm_angles_degrees)

        # Move the right arm
        self.move_arm("R", right_arm_angles_radians, speed=0.1)

        # Move the left arm
        self.move_arm("L", left_arm_angles_radians, speed=0.1)

    ### Looping Arm Motion ###
    def bicep_curls(self):
        """
        Moves Pepper's arms up and down for bicep curls until stopped.
        """
        rospy.loginfo("Pepper is performing bicep curls.")
        rospy.loginfo("-"*20)
        try:
            while self.exercise_running and not rospy.is_shutdown():
                print()
                rospy.loginfo("[!!] self.exercise_running = {}".format(self.exercise_running))
                print()
                
                self.bicep_arm_motion_up()
                rospy.loginfo("Arms moved up.")
                
                rospy.sleep(2)

                self.bicep_arm_motion_down()
                rospy.loginfo("Arms moved down.")
                rospy.sleep(2)

            rospy.loginfo("Bicep curls stopped. Entering rest phase.")
            self.exercise_running = False
            self.current_exercise = None
            self.is_resting = True
            self.exercise_publisher.publish("rest")

        except rospy.ROSInterruptException:
            rospy.loginfo("Bicep curls interrupted.")

    def lateral_raises(self):
        """
        Moves Pepper's arms outward for lateral raises until stopped.
        """
        rospy.loginfo("Pepper is performing lateral raises.")

        try:
            while self.exercise_running and not rospy.is_shutdown():
                self.lateral_arm_motion_up()
                rospy.loginfo("Arms moved up.")
                
                rospy.sleep(2)

                self.lateral_arm_motion_down()
                rospy.loginfo("Arms moved down.")
                rospy.sleep(2)

            rospy.loginfo("Lateral raises stopped. Entering rest phase.")
            self.exercise_running = False
            self.current_exercise = None
            self.is_resting = True
            self.exercise_publisher.publish("rest")

        except rospy.ROSInterruptException:
            rospy.loginfo("Lateral raises interrupted.")

    ### Look Back Motion ###
    def look_back(self):
        """
        Pepper looking toward the user.
        """
        rospy.loginfo("Pepper is looking back.")

        # go to an init head pose.
        names  = ["HeadYaw", "HeadPitch"]
        angles = [0.0, 0.0]
        times  = [1.0, 1.0]
        self.motion.angleInterpolation(names, angles, times, True)

    def look_away(self):
        # tilting head
        rospy.loginfo("Pepper is looking away.")

        names  = ["HeadYaw", "HeadPitch"]
        angles = [-math.pi/5, 0.2]
        times  = [2.0, 3.0]
        self.motion.angleInterpolation(names, angles, times, True, _async=True)

    def random_head_move(self):
        rospy.loginfo("Pepper is randomly moving head.")

        names  = ["HeadYaw", "HeadPitch"]
        angles = [-math.pi/5, 0.2]
        times  = [2.0, 3.0]
        self.motion.angleInterpolation(names, angles, times, True, _async=True)

    def nod_head(self):
        rospy.loginfo("Pepper is nodding.")
        
        # Define the head movement for nodding (pitch angle)
        names = ["HeadPitch"]
        # Nodding down and up
        angles = [-0.1, 0.1]
        # Time to complete the two movements
        times = [2.0, 2.0]  # 1.5 seconds for each nod
        
        # Perform the nodding motion twice in 3 seconds
        self.motion.angleInterpolation(names, angles, times, True, _async=True)

    def pub_image(self):
        image = self.video_service.getImageRemote(self.subscriber_id)
        if image:
            width = image[0]
            height = image[1]
            timestamp = rospy.Time.now()

            # Create ROS Image message
            ros_image = Image()
            #ros_image.header = Header()
            ros_image.header.stamp = timestamp
            ros_image.width = width
            ros_image.height = height
            ros_image.encoding = "rgb8"
            #ros_image.is_bigendian = 0
            ros_image.step = width * 3  # 3 bytes per pixel (RGB)
            ros_image.data = image[6]  # Image pixel data

            # Publish to ROS topic
            self.image_publisher.publish(ros_image)
            # rospy.loginfo("Published a frame from Pepper.")s
    
    def listener(self):
        """
        Start the ROS listener node and execute the arm motion loop.
        """
        rospy.loginfo("Starting listener...")
        self.move_arms_up_and_down()

    def start_rosbag_video_recording(self):
        filename = "video_only_p{}_week{}_{}.bag".format(
            self.participant_number, self.week_number, self.timestamp
        )
        save_path = os.path.join(self.recordings_dir, filename)
        rospy.loginfo("Starting rosbag video recording: {}".format(save_path))
        self.rosbag_process = subprocess.Popen(
            ["rosbag", "record", "-O", save_path, "/pepper_camera/image_raw"]
        )

    def stop_rosbag_video_recording(self):
        if hasattr(self, 'rosbag_process') and self.rosbag_process:
            rospy.loginfo("Stopping rosbag video recording...")
            self.rosbag_process.terminate()
            self.rosbag_process.wait()

    def start_system_audio_recording(self):
        try:
            filename = "local_audio_p{}_week{}_{}.wav".format(
                self.participant_number, self.week_number, self.timestamp
            )
            self.audio_file = os.path.join(self.recordings_dir, filename)
            cmd = ["arecord", "-f", "cd", "-t", "wav", self.audio_file]
            rospy.loginfo("Starting system audio recording: {}".format(self.audio_file))
            self.audio_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.recording = True
            return True
        except Exception as e:
            rospy.logerr("Failed to start system audio recording: {}".format(e))
            return False

    def stop_system_audio_recording(self):
        try:
            if self.audio_process and self.recording:
                rospy.loginfo("Stopping system audio recording...")
                self.audio_process.terminate()
                self.audio_process.wait()
                self.recording = False
        except Exception as e:
            rospy.logerr("Error stopping system audio recording: {}".format(e))

    def cleanup_audio(self):
        try:
            if self.recording:
                self.stop_system_audio_recording()
        except Exception as e:
            rospy.logerr("Error during audio cleanup: {}".format(e))
    
    def main(self):
        rate = rospy.Rate(5)  # 10hz
        # rospy.Subscriber("move_arm_command", String, pepper_listener.move_arm_callback)
        while not rospy.is_shutdown():
            #publish camera image
            self.pub_image()
            rate.sleep()
        
if __name__ == '__main__':
    rospy.init_node('pepper_controller', anonymous=True)
    pepper_listener = Pepper()
    pepper_listener.main()