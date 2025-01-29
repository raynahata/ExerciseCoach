# This node file should be run on Python 2.7
# Ensure PYTHONPATH includes the naoqi SDK for Python 2.7
# Example:
# export PYTHONPATH=${PYTHONPATH}:/path/to/pynaoqi-python2.7/lib/python2.7/site-packages

import rospy
from naoqi import ALProxy
from std_msgs.msg import String
import time
import almath


class PepperController:
    def __init__(self, ip="128.237.236.27", port=9559):
        # Connection setup
        self.IP = ip
        self.PORT = port
        self.tts = ALProxy("ALTextToSpeech", self.IP, self.PORT)
        self.motion = ALProxy("ALMotion", self.IP, self.PORT)
        self.posture = ALProxy("ALRobotPosture", self.IP, self.PORT)
        self.tablet = ALProxy("ALTabletService", self.IP, self.PORT)

        # Set TTS parameters
        self.tts.setParameter("defaultVoiceSpeed", 70)

        # State variables
        self.state = ""
        self.current_text = ""

        # ROS Publishers and Subscribers
        rospy.init_node("pepper_controller", anonymous=True)
        self.state_pub = rospy.Publisher("pepper_state", String, queue_size=10)
        self.text_pub = rospy.Publisher("chat_text", String, queue_size=10)
        rospy.Subscriber("pepper_state", String, self.callback_state)
        rospy.Subscriber("chat_text", String, self.callback_text)

    ### Actions ###
    def display_text_on_tablet(self, text):
        """
        Display the given text on Pepper's tablet.
        """
        rospy.loginfo(f"Displaying text on tablet: {text}")
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    background-color: #f5f5f5;
                    margin-top: 100px;
                }}
                h1 {{
                    color: #333;
                }}
            </style>
        </head>
        <body>
            <h1>{text}</h1>
        </body>
        </html>
        """
        # Load the HTML content on the tablet
        self.tablet.showWebview("http://198.18.0.1/apps/boot-config/empty.html")  # Blank page
        self.tablet.loadHtml(html_content)

    def say_text(self, text):
        """
        Make Pepper say the provided text.
        """
        rospy.loginfo(f"Saying: {text}")
        self.tts.say(text)

    ### State Management ###
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

    ### Callbacks ###
    def callback_text(self, data):
        """
        Callback for 'chat_text' topic.
        """
        rospy.loginfo(f"Received text: {data.data}")
        self.current_text = data.data
        self.set_flag_speaking()
        self.say_text(self.current_text)
        self.display_text_on_tablet(self.current_text)
        self.set_flag_listening()

    def callback_state(self, data):
        """
        Callback for 'pepper_state' topic.
        """
        rospy.loginfo(f"Received state: {data.data}")
        self.state = data.data

    def publish_text(self, text):
        """
        Publish text to the 'chat_text' topic.
        """
        rospy.loginfo(f"Publishing text: {text}")
        self.text_pub.publish(text)

    def run(self):
        """
        Start the ROS event loop to keep the node running.
        """
        rospy.loginfo("Starting Pepper Controller")
        while not rospy.is_shutdown():
            user_input = input("Enter text to send ('quit' to exit): ")
            if user_input.lower() == "quit":
                break
            self.publish_text(user_input)
        rospy.spin()


if __name__ == "__main__":
    try:
        # Replace IP with your Pepper's IP address
        pepper_controller = PepperController(ip="128.237.236.27", port=9559)
        pepper_controller.run()
    except rospy.ROSInterruptException:
        rospy.loginfo("Shutting down Pepper Controller")