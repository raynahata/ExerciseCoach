# This node file should be run on Python 2.7
# export PYTHONPATH=${PYTHONPATH}:/home/raynahata/exercise_bot/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages

import rospy
from naoqi import ALProxy
import math
import time
from std_msgs.msg import String


class Pepper:
    def __init__(self):
        self.IP = "128.237.236.27"
        self.tts = ALProxy("ALTextToSpeech", self.IP, 9559)
        self.motion = ALProxy("ALMotion", self.IP, 9559)
        self.posture = ALProxy("ALRobotPosture", self.IP, 9559)
        self.life = ALProxy('ALAutonomousLife', self.IP, 9559)
        self.life.setAutonomousAbilityEnabled("All", False)
        self.life.stopAll()
        self.tablet=ALProxy("ALTabletService",self.IP,9559)

        self.tts.setParameter("defaultVoiceSpeed", 70)
        self.exercise_running=False
        
        self.state = ""
        self.current_text = ""

        # ROS Publishers and Subscribers
        rospy.init_node("pepper_controller", anonymous=True)
        self.state_pub = rospy.Publisher("pepper_state", String, queue_size=10)
        self.text_pub = rospy.Publisher("chat_text", String, queue_size=10)
        rospy.Subscriber("pepper_state", String, self.callback_state)
        #rospy.Subscriber("chat_text", String, self.callback_text)
        rospy.Subscriber("gpt_speech", String, self.gpt_callback)
        rospy.Subscriber("exercise_command", String, self.exercise_callback)
        rospy.loginfo("Subscribed to /gpt_speech")

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
        Callback for /exercise_command topic.
        If "bicep curls" is received, start the exercise.
        If "rest" is received, stop the exercise.
        """
        rospy.loginfo("Received exercise command: {}".format(msg.data))
        command = msg.data.lower()

        if command == "bicep curls":
            if not self.exercise_running:
                rospy.loginfo("Starting bicep curls...")
                self.exercise_running = True
                self.bicep_curls()
            else:
                rospy.loginfo("Exercise is already running.")

        elif command == "lateral raises":
            if not self.exercise_running:
                rospy.loginfo("Starting lateral raises...")
                self.exercise_running = True
                self.lateral_raises()
            else:
                rospy.loginfo("Exercise is already running.")

        elif command == "rest":
            if self.exercise_running:
                rospy.loginfo("Stopping exercise...")
                self.exercise_running = False  # Stop any running exercise

            else:
                rospy.loginfo("No exercise is currently running.")



    
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
        self.set_flag_listening()

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

    ### Hardcoded Arm Motion: Up ###
    def stop_exercise_motion(self):
        self.posture.goToPosture("StandInit", 0.5)
        
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
        Continuously move the arms up and down until the program is stopped.
        """
        rospy.loginfo("Starting to move arms up and down...")
       
        self.posture.goToPosture("StandInit", 0.5)
    

        try:
            while not rospy.is_shutdown() and self.exercise_running:
                
                
                # Move arms up
                self.bicep_arm_motion_up()
                #self.bicep_arm_motion_up()
                rospy.loginfo("Arms moved up.")
                time.sleep(2)  # Wait for 2 seconds

                # Move arms down
                self.bicep_arm_motion_down()
                #self.bicep_arm_motion_down()
                rospy.loginfo("Arms moved down.")
                time.sleep(2)  # Wait for 2 seconds
                
               
                     
        except rospy.ROSInterruptException:
            rospy.loginfo("Shutting down arm motion.")

    def lateral_raises(self):
        """
        Continuously move the arms up and down until the program is stopped.
        """
        rospy.loginfo("Starting to move arms up and down...")
       
        self.posture.goToPosture("StandInit", 0.5)
    
        try:
            while not rospy.is_shutdown() and self.exercise_running:
                
                
                # Move arms up
                self.lateral_arm_motion_up()
                #self.bicep_arm_motion_up()
                rospy.loginfo("Arms moved up.")
                time.sleep(2)  # Wait for 2 seconds

                # Move arms down
                self.lateral_arm_motion_down()
                #self.bicep_arm_motion_down()
                rospy.loginfo("Arms moved down.")
                time.sleep(2)  # Wait for 2 seconds
        except rospy.ROSInterruptException:
            rospy.loginfo("Shutting down arm motion.")

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