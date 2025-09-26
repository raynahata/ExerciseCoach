#!/usr/bin/env python
# -*- coding: utf-8 -*-

from naoqi import ALProxy

PEPPER_IP = "192.168.1.113"   # Replace with Pepper's IP
PORT = 9559

battery = ALProxy("ALBattery", PEPPER_IP, PORT)

# Battery charge percentage
print("Battery level:", battery.getBatteryCharge(), "%")

# Charging state (True/False)
print("Is charging:", battery.isCharging())

