from naoqi import ALProxy
import math
import time

class Pepper:
    
    def __init__(self, ip='128.237.236.27'):
        self.IP = ip
        self.life = self.proxy_events('ALAutonomousLife')
        self.life.setAutonomousAbilityEnabled("All", False)
        self.life.stopAll()

    def proxy_events(self, topic):
        return ALProxy(topic, self.IP, 9559)

    def thinking_motion(self):
        motion_service = self.proxy_events('ALMotion')

        # Wake up robot
        motion_service.wakeUp()

        # go to an init head pose.
        names  = ["HeadYaw", "HeadPitch", 
                "RElbowRoll", "RShoulderPitch", 
                "RShoulderRoll", "RWristYaw",
                "RElbowYaw"] 
        angles = [0.0, 0.0, 
                0.0, math.pi/2, 
                -math.pi/8, 0.0, 
                math.pi/2-0.4]
        times  = [1.0, 1.0, 
                1.0, 1.0, 
                1.0, 1.0,
                1.0]
        isAbsolute = True
        motion_service.angleInterpolation(names, angles, times, isAbsolute)

        tts = self.proxy_events("ALTextToSpeech")
        tts.say("o")

        # tilting head and arm lifting
        names  = ["HeadYaw", "HeadPitch", 
                "RElbowRoll", "RShoulderPitch", 
                "RWristYaw"]
        angles = [-math.pi/5, 0.2, 
                math.pi/2, 0.0,
                math.pi/3]
        times  = [2.0, 3.0, 
                1.0, 1.0, 
                1.0]
        isAvailable = motion_service.areResourcesAvailable(names)
        print("areResourcesAvailable({0}): {1}".format(names, isAvailable))
        motion_service.angleInterpolation(names, angles, times, isAbsolute, _async=True)
        print("[!] Head tilt and arm lifting finished!")

        time.sleep(3)

        # go to an init head pose.
        names  = ["HeadYaw", "HeadPitch", 
            "RElbowRoll", "RShoulderPitch", 
            "RWristYaw"] 
        angles = [0.0, 0.0, 
                0.0, math.pi/2, 
                0.0]
        times  = [1.0, 1.0, 
                1.0, 1.0,
                1.0]
        isAbsolute = True
        motion_service.angleInterpolation(names, angles, times, isAbsolute)

if __name__ == "__main__":
    robot = Pepper()
    a = input("pasuing...")
    robot.thinking_motion()

