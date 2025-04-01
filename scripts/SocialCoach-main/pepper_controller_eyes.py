# This node file should be run on Python 2.7
# export PYTHONPATH=${PYTHONPATH}:/home/raynahata/exercise_bot/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages

import rospy
from naoqi import ALProxy
import math
import time
from std_msgs.msg import String
import threading
import os


class Pepper:
    def __init__(self):
        self.IP = "128.237.236.27"
        self.tts = ALProxy("ALTextToSpeech", self.IP, 9559)
        self.motion = ALProxy("ALMotion", self.IP, 9559)
        self.posture = ALProxy("ALRobotPosture", self.IP, 9559)
        self.life = ALProxy('ALAutonomousLife', self.IP, 9559)
        # self.life.setAutonomousAbilityEnabled("All", True)
        self.life.setAutonomousAbilityEnabled("All", False)
        self.life.stopAll()
        self.tablet = ALProxy("ALTabletService",self.IP,9559)
        self.memory = ALProxy("ALMemory", self.IP, 9559)
        self.leds = ALProxy("ALLeds", self.IP, 9559)
        self.tts.setParameter("defaultVoiceSpeed", 70)
        self.tts.setParameter("pitchShift", 1)

        self.videoRecorder = ALProxy("ALVideoRecorder", self.IP, 9559)
        self.videoRecorder.setResolution(2)  # 640x480
        self.videoRecorder.setFrameRate(10)  # 30 FPS
        self.videoRecorder.setVideoFormat("MP4")
        



        
        self.exercise_running=False
        self.pepper_thinking = False

        
        self.state = ""
        self.current_text = ""

        # ROS Publishers and Subscribers
        rospy.init_node("pepper_controller", anonymous=True)
        self.state_pub = rospy.Publisher("pepper_state", String, queue_size=10)
        self.text_pub = rospy.Publisher("chat_text", String, queue_size=10)
        self.exercise_publisher = rospy.Publisher("/exercise_command", String, queue_size=10)
        rospy.Subscriber("pepper_state", String, self.callback_state)
        rospy.Subscriber("gpt_speech", String, self.gpt_callback)
        rospy.Subscriber("speech_display", String, self.display_callback)
        rospy.Subscriber("exercise_command", String, self.exercise_callback)
        rospy.Subscriber("/pepper_video_control", String, self.video_command_callback)



        rospy.loginfo("Subscribed to /gpt_speech")

        self.exercise_running = False  # True when an exercise is running
        self.current_exercise = None  # Stores the name of the current exercise
        self.is_resting = False  # True when Pepper is resting

        rospy.loginfo("Subscribed to /exercise_command topic.")

    def start_video_recording(self, participant_ID, week, session_type):
        """
        Start video recording.
        """
        rospy.loginfo("Starting video recording...")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        recordings_folder = os.path.join(base_dir, "recordings")
        os.makedirs(recordings_folder, exist_ok=True)

        video_filename = "participant_{}_week_{}_{}.mp4".format(participant_ID, week, session_type)
        video_file_path = os.path.join(recordings_folder, video_filename)

        self.videoRecorder.startRecording(video_file_path)
        rospy.loginfo("Recording video to: {}".format(video_file_path))
        time.sleep(2)

        if self.videoRecorder.isRecording():
            rospy.loginfo("Recording is in progress.")
        else:
            rospy.loginfo("Recording failed to start.")
        return video_file_path
    
    def stop_video_recording(self):
        """
        Stop video recording.
        """
        rospy.loginfo("Stopping video recording...")
        self.videoRecorder.stopRecording()
        # Check if recording has stopped
        recording_status = self.videoRecorder.isRecording()
        if not recording_status:
            rospy.loginfo("Recording stopped successfully.")
        else:
            rospy.loginfo("Failed to stop recording.")

    def video_command_callback(self, data):
        """
        Callback for video control commands.
        Expected format:
        'start recording;participant_#;week_#;session_type'
        or
        'stop recording'
        """
        rospy.loginfo("Received video command: {}".format(data.data))
        tokens = data.data.strip().lower().split(";")

        if tokens[0] == "start recording":
            if not self.exercise_running:
                if len(tokens) >= 4:
                    participant_id = tokens[1].replace("participant_", "")
                    week = tokens[2].replace("week_", "")
                    session_type = tokens[3]  # e.g., 'intro' or 'exercise'
                    self.start_video_recording(participant_id, week, session_type)
                else:
                    rospy.logwarn("Invalid video start format. Use 'start recording;participant_#;week_#;session_type'")
            else:
                rospy.loginfo("Cannot start recording during exercise.")
        elif tokens[0] == "stop recording":
            self.stop_video_recording()
        
        
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
                threading.Thread(target=self.lateral_raises()).start()
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
        self.say_text(self.current_text)
        # self.display_text(self.current_text)
        while (self.memory.getData("ALTextToSpeech/Status"))[1] != "done":
            time.sleep(0.1)
        rospy.loginfo("Finished Speaking...")
        time.sleep(0.1)
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


    def listener(self):
        """
        Start the ROS listener node and execute the arm motion loop.
        """
        rospy.loginfo("Starting listener...")
        self.move_arms_up_and_down()

    def main():
        rospy.init_node('pepper_controller', anonymous=True)
        pepper_listener = Pepper(ip="128.237.236.27", port=9559)

        try:
            rospy.spin()  # Keep the node running
        except KeyboardInterrupt:
            rospy.loginfo("Shutting down Pepper Listener.")

if __name__ == '__main__':
    rospy.init_node('pepper_controller', anonymous=True)
    pepper_listener = Pepper()
    pepper_listener.clear_screen()

    try:
        rospy.spin()  # Keep the node running
    except KeyboardInterrupt:
        rospy.loginfo("Shutting down Pepper Listener.")