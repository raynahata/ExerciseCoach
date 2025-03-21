from naoqi import ALProxy
import time
class Test():
    def __init__(self):
        self.IP = "128.237.236.27"
        self.ledProxy = ALProxy("ALLeds", self.IP, 9559)
    def set_eye_color(self, color):
        r, g, b = color
        hex_color = (r << 16) | (g << 8) | b  # Convert to hex format
        self.ledProxy.fadeRGB("FaceLeds", hex_color, 0.3)

if __name__ == "__main__":
    P = Test()
    print("Yellow")

    P.set_eye_color((255,255,0))
    time.sleep(2)
    print("White")
    time.sleep(2)
    P.set_eye_color((255,255,255))
    print("Blue")
    time.sleep(2)

    P.set_eye_color((0,0,255))