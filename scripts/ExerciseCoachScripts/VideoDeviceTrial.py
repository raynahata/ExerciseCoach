# This test demonstrates how to use the ALVideoRecorder module.
#different from ALVideoDevice module! 
# Note that you might not have this module depending on your distribution
import rospy
from naoqi import ALProxy
import math
import time
import sys
import os
from std_msgs.msg import String
import numpy as np
import cv2

class Pepper:
    def __init__(self):
        self.IP = "128.237.236.27"
        #first instantiate a proxy to the ALVideoDevice module.
        self.videoDeviceProxy = ALProxy("ALVideoDevice", self.IP, 9559)

#Make your vision module subscribe to the ALVideoDevice proxy:
#do this by calling ALVideoDeviceProxy::subscribeCamera and passing it parameters:
# such as resolution, color space and frame rate.
    def start_video_stream(self):
        resolution = 2  # Set resolution to VGA (640 x 480)
        color_space = 13
        frame_rate = 10
        video_client = self.videoDeviceProxy.subscribe("video_stream", resolution, color_space, frame_rate)
        return video_client


#Stop video streaming from Pepper's camera.
    def stop_video_stream(self, video_client):
        pepper_listener = Pepper()
        # Start video stream and capture an image
        video_client = pepper_listener.start_video_stream()
        self.videoDeviceProxy.unsubscribe(video_client)

    def capture_image(self, video_client):
        """
        Capture a single frame from the video stream.
        """
        # Get a frame from the camera
        frame = self.video_device.getImageRemote(video_client)
        if frame is None:
            rospy.logwarn("No image data received.")
            return None
        
        # Extract image data
        width, height, color_space, timestamp, data = frame
        image = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

        # Convert the image to BGR (OpenCV format)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # Save or display the image (optional)
        file_name = f"pepper_image_{timestamp}.png"
        cv2.imwrite(file_name, image_bgr)
        rospy.loginfo(f"Image saved as {file_name}.")
        return image_bgr


#In the main process loop, get an image by calling ALVideoDeviceProxy::getImageLocal 
#or ALVideoDeviceProxy::getImageRemote (depending on whether your module is local or remote).
#Release the image calling ALVideoDeviceProxy::releaseImage,
#When you stop your module, call ALVideoDeviceProxy::unsubscribe after exiting the main loop.
    def main(self):
        rospy.init_node('pepper_controller', anonymous=True)
        pepper_listener = Pepper()
        # Start video stream and capture an image
        video_client = pepper_listener.start_video_stream()

        try:
            # Capture an image after starting video stream
            image = pepper_listener.capture_image(video_client)
            if image is not None:
                rospy.loginfo("Captured an image from Pepper's camera.")

            rospy.spin()  # Keep the node running
        except KeyboardInterrupt:
            rospy.loginfo("Shutting down Pepper Listener.")
        finally:
            # Stop video stream when done
            pepper_listener.stop_video_stream(video_client)


if __name__ == '__main__':
    rospy.init_node('pepper_controller', anonymous=True)
    pepper_listener = Pepper()
    pepper_listener.clear_screen()

    try:
        rospy.spin()  # Keep the node running
    except KeyboardInterrupt:
        rospy.loginfo("Shutting down Pepper Listener.")

#videoRecorderProxy.setFrameRate(10.0)
#videoRecorderProxy.setResolution(2) # Set resolution to VGA (640 x 480)
# We'll save a 5 second video record in /home/nao/recordings/cameras/
#videoRecorderProxy.startRecording("/home/nao/recordings/cameras", "test")
#print("Video record started.")

#time.sleep(5)

#videoInfo = videoRecorderProxy.stopRecording()
#print("Video was saved on the robot: ", videoInfo[1])
#print("Total number of frames: ", videoInfo[0])