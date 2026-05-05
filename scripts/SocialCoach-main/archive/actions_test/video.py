import cv2
import numpy as np
from naoqi import ALProxy
from flask import Flask, Response

# Replace with Pepper's IP address
PEPPER_IP = "128.237.236.27"
PORT = 9559

# Connect to Pepper's camera
video_device = ALProxy("ALVideoDevice", PEPPER_IP, PORT)
camera_index = 0  # 0 = top camera, 1 = bottom camera, 2 = depth camera

# Set resolution and frame rate
resolution = 2  # 640x480
color_space = 13  # RGB
fps = 15  # Frames per second

# Subscribe to video feed
capture_device = video_device.subscribeCamera("camera_stream", camera_index, resolution, color_space, fps)

# Set up Flask web server
app = Flask(__name__)

def generate_frames():
    """
    Captures frames from Pepper's camera and streams them over HTTP.
    """
    while True:
        # Get an image from the camera
        img = video_device.getImageRemote(capture_device)
        if img is None:
            continue  # Skip this frame if there is an issue

        # Extract image data
        width = img[0]
        height = img[1]
        array = np.frombuffer(img[6], dtype=np.uint8).reshape((height, width, 3))

        # Convert the image to JPEG format
        _, jpeg = cv2.imencode('.jpg', array)
        frame = jpeg.tobytes()

        # Yield the frame as part of an HTTP stream
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    """
    Route to stream video from Pepper's camera.
    """
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)