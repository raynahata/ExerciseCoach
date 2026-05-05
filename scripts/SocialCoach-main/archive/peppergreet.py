#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from naoqi import ALProxy

class PepperGreeter:
    def __init__(self, ip="172.20.10.7", port=9559):
        self.ip = ip
        self.port = port

        # Core modules
        self.motion = ALProxy("ALMotion", self.ip, self.port)
        self.tts = ALProxy("ALTextToSpeech", self.ip, self.port)
        self.memory = ALProxy("ALMemory", self.ip, self.port)
        self.people = ALProxy("ALPeoplePerception", self.ip, self.port)
        self.tablet = ALProxy("ALTabletService", self.ip, self.port)
        self.awareness = ALProxy("ALBasicAwareness", self.ip, self.port)

        # Manual awareness setup (without Autonomous Life)
        self.awareness.setTrackingMode("Head")
        self.awareness.setEngagementMode("FullyEngaged")
        self.awareness.setStimulusDetectionEnabled("People", True)
        self.awareness.startAwareness()

        # People perception
        try:
            self.people.setEnabled(True)
            self.people.setFastModeEnabled(True)
            print("People perception enabled.")
        except RuntimeError:
            print("Could not enable PeoplePerception.")

        # Speech settings
        self.tts.setLanguage("English")
        self.tts.setParameter("speed", 70)

        # Tablet
        self.tablet.hide()

        self.has_greeted = False

    def display_text(self, text):
        html = """
        <body style='background-color:white;display:flex;align-items:center;justify-content:center;height:100vh;'>
        <p style='font-size:50px;text-align:center;color:black;'>{}</p>
        </body>
        """.format(text)
        self.tablet.showWebview("data:text/html;charset=utf-8," + html)

    def say_hello(self):
        message = "Hi, I'm Pepper. Will you exercise with me?"
        self.display_text(message)
        self.tts.say(message)

    def run(self):
        print("Starting PeoplePerception detection loop...")
        while True:
            try:
                visible_ids = self.memory.getData("PeoplePerception/VisiblePeopleList")
            except RuntimeError:
                visible_ids = []

            if visible_ids and not self.has_greeted:
                print("Person detected (IDs: {}). Greeting...".format(visible_ids))
                self.say_hello()
                self.has_greeted = True
            elif not visible_ids:
                self.has_greeted = False

            time.sleep(1.5)

if __name__ == "__main__":
    greeter = PepperGreeter()
    greeter.run()
