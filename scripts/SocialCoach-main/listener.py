# This node file should be run on python 2.7
# export PYTHONPATH=${PYTHONPATH}:/home/raynahata/exercise_bot/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages
import rospy
from naoqi import ALProxy
import qi
from std_msgs.msg import String
import time
import almath

class PepperListener:
    def __init__(self):
        self.IP = "128.237.236.27"
        self.tts = ALProxy("ALTextToSpeech", self.IP, 9559)

        self.motion = ALProxy("ALMotion", self.IP, 9559)
        self.posture = ALProxy("ALRobotPosture", self.IP, 9559)
        # ALProxy("ALListeningMovementProx", "128.237.236.27", 9559)
        self.tts.setParameter("defaultVoiceSpeed", 70)
        self.state = ""
        self.current_text = ""

        # display = ALProxy("ALTabletService", "128.237.236.27", 9559)
        # display.showWebview("https://www.cmu.edu")
        # photo = ALProxy("ALPhotoCapture", "128.237.236.27", 9559)
        # /home/raynahata/exercise_bot/photos
        
        # autonomous = ALProxy("ALAutonomousLife", "128.237.236.27", 9559)
        # autonomous.setAutonomousAbilityEnabled("AutonomousBlinking", True)
        # autonomous.setAutonomousAbilityEnabled("BackgroundMovement", True)
        # autonomous.setAutonomousAbilityEnabled("BasicAwareness", False)
        # autonomous.setAutonomousAbilityEnabled("ListeningMovement", True)
        # autonomous.setAutonomousAbilityEnabled("SpeakingMovement", True)

    # def display_text(text):
    #     # document.querySelector('h1').textContent = "Hi"
    #     script = '''
    #     c.textContent = ;''' + text
    #     display.executeJS(script)

    def action_listening(self):
        # for _ in range(2):
        #     fractionMaxSpeed = 0.3
        #     self.motion.setAngles("HeadPitch", 10*almath.TO_RAD, fractionMaxSpeed)
        #     time.sleep(3)
        pass

    def action_speaking(self):
        # self.posture.goToPosture("StandInit", 1.0)
        # time.sleep(2)
        pass

    def set_flag_listening(self):
        self.state = "listening"   # setting the flag back to listening mode
        self.action_listening()
    
    def set_flag_speaking(self):
        self.state = "speaking"   # setting the flag back to listening mode
        self.action_speaking()
    
    def run_tts(self):
        self.set_flag_speaking()
        self.tts.say(self.current_text)
        self.set_flag_listening()
        # if self.state == "speaking":
        #     self.set_flag_speaking()
        #     self.tts.say(self.current_text)
        #     self.set_flag_listening()
        # else:
        #     rospy.loginfo(rospy.get_caller_id() + "CURRENT STATE IS: %s, SHOULD NOT CALL TTS", self.state)
    
    def callback_text(self, data):
        rospy.loginfo(rospy.get_caller_id() + "RECIEVING TEXT: %s", data.data)
        self.current_text = data.data
        self.run_tts()
        
    def callback_state(self, data):
        rospy.loginfo(rospy.get_caller_id() + "RECIEVING STATE: %s", data.data)
        self.state = data.data  # setting flag everytime when it receives one

    def listener(self):

        rospy.init_node('listener', anonymous=True)

        rospy.Subscriber("pepper_state", String, self.callback_state)

        rospy.Subscriber("chat_text", String, self.callback_text)

        rospy.spin()

if __name__ == '__main__':
    pepper_listener = PepperListener()
    pepper_listener.listener()