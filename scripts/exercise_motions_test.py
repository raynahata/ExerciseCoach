# This node file should be run on Python 2.7
# export PYTHONPATH=${PYTHONPATH}:/path/to/naoqi-sdk/lib/python2.7/site-packages

import rospy
from naoqi import ALProxy
import math
import time


class PepperListener:
    # Pepper IP address is  128.237.236.27
    def __init__(self,ip_address="128.237.236.27",port=9559):
        self.IP =ip_address
        self.port=port


        self.tts = ALProxy("ALTextToSpeech", self.IP,self.port)
        self.motion = ALProxy("ALMotion", self.IP,self.port)
        self.posture = ALProxy("ALRobotPosture", self.IP,self.port)
        self.autonomous_life = ALProxy('ALAutonomousLife',self.IP,self.port)
        self.tablet=ALProxy("ALTabletService",self.IP,self.port)
        self.voice_emotion_detection=ALProxy("ALVoiceEmotionAnalysis",self.IP,self.port)
        self.sound_detection=ALProxy("ALSoundDetection",self.IP,self.port)
        self.animated_speech=ALProxy("ALAnimatedSpeech",self.IP,self.port)
        self.person_mood=ALProxy("ALMood",self.IP,self.port)
        self.basic_awareness=ALProxy("ALBasicAwareness",self.IP,self.port)


        self.autonomous_life.setAutonomousAbilityEnabled("All", True)
        self.basic_awareness.setTrackingMode("Head")  # Prevents head from tracking faces or objects


        #self.life.stopAll()
    
        self.tts.setParameter("defaultVoiceSpeed", 70)

        # Initialize ROS node
        rospy.init_node('listener', anonymous=True)

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

    def display_feedback(self, message):
        """

        Display the given message by directing Pepper's tablet to a webpage.
        Args:
        url: The URL of the webpage to display.
        """
        #rospy.loginfo("Displaying webpage on tablet: {}".format(url))
        #self.tablet.showWebview(url)
        rospy.loginfo("Displaying message on tablet: {}".format(message))
        js_script = """
                document.body.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100vh; text-align: center;">'
                            + '<h1 style="font-family: Arial, sans-serif; font-size: 80px; font-weight: bold; color: black;">{}</h1>'
                            + '</div>';
        """.format(message)
        self.tablet.executeJS(js_script)
        

    ### Hardcoded Arm Motion: Up ###
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
    def move_arms_up_and_down(self):
        """
        Continuously move the arms up and down until the program is stopped.
        """
        rospy.loginfo("Starting to move arms up and down...")
        #feedback_url = "http://<172.26.222.60>:8000/bicep_curls.html"  # Replace with your local server URL
        #self.display_feedback(feedback_url)
        self.display_feedback("Doing bicep curls")

        try:
            while not rospy.is_shutdown():
                self.display_feedback("Doing bicep curls")
                #feedback_url = "http://<172.26.222.60>:8000/bicep_curls.html"  # Replace with your local server URL
                #self.display_feedback(feedback_url)
                # Move arms up
                #self.lateral_arm_motion_up()
                self.bicep_arm_motion_up()
                rospy.loginfo("Arms moved up.")
                time.sleep(2)  # Wait for 2 seconds

                # Move arms down
                self.bicep_arm_motion_down()
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


if __name__ == '__main__':
    try:
        pepper_listener = PepperListener()
        pepper_listener.listener()
    except rospy.ROSInterruptException:
        rospy.loginfo("Shutting down Pepper Listener.")