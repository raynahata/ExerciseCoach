# This node file should be run on python 3
import rospy
from std_msgs.msg import String
import time

def talker_init():
    pub_text = rospy.Publisher('chat_text', String, queue_size=10)
    pub_state = rospy.Publisher('pepper_state', String, queue_size=10)
    rospy.init_node('talker', anonymous=True)
    rate = rospy.Rate(10) # 10hz
    return pub_text, pub_state, rate

# def talker(text):
#     pub_text = rospy.Publisher('chat_text', String, queue_size=10)
#     pub_state = rospy.Publisher('pepper_state', String, queue_size=10)
#     rospy.init_node('talker', anonymous=True)
#     rate = rospy.Rate(10) # 10hz
#     while True:
#         pub_state.publish("listening")  # setting flag

#         user_input_str = input("Text Input: ")
#         if user_input_str == "quit":
#             break
#         pub_state.publish("speaking")   # setting flag
#         time.sleep(0.3)
#         pub_text.publish(user_input_str)
#         rate.sleep()

def talker(text, pub_state, pub_text, rate):
    pub_state.publish("listening")  # setting flag
    pub_state.publish("speaking")   # setting flag
    time.sleep(0.3)
    pub_text.publish(text)
    rate.sleep()


if __name__ == '__main__':
    try:
        talker()
    except rospy.ROSInterruptException:
        pass