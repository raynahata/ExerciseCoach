# pepper_cam_bridge.py  Python 2.7
import rospy
from sensor_msgs.msg import Image
from naoqi import ALProxy

PEPPER_IP = "192.168.1.113"
PORT = 9559

CAMERA_INDEX = 0      # 0 is top camera which is front
RESOLUTION = 2        # 640x480
COLOR_SPACE = 11      # RGB
FPS = 10

def main():
    rospy.init_node("pepper_cam_bridge", anonymous=True)
    pub = rospy.Publisher("/pepper_camera/image_raw", Image, queue_size=1)

    vdev = ALProxy("ALVideoDevice", PEPPER_IP, PORT)
    name = vdev.subscribeCamera("pepper_cam_bridge", CAMERA_INDEX, RESOLUTION, COLOR_SPACE, FPS)

    rate = rospy.Rate(FPS)
    try:
        while not rospy.is_shutdown():
            img = vdev.getImageRemote(name)
            if not img:
                rate.sleep()
                continue

            w, h = img[0], img[1]
            data = img[6]

            msg = Image()
            msg.header.stamp = rospy.Time.now()
            msg.height = h
            msg.width = w
            msg.encoding = "rgb8"
            msg.step = w * 3
            msg.data = data

            pub.publish(msg)
            rate.sleep()
    finally:
        try:
            vdev.unsubscribe(name)
        except:
            pass

if __name__ == "__main__":
    main()
