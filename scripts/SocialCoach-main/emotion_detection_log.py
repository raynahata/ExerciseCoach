#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

import qi
from naoqi import ALBroker, ALModule
import argparse
import sys
import time
import random
import os
from datetime import datetime

# ========== EDIT THESE VALUES ==========
PARTICIPANT_NUMBER = 1  # Change this to the participant number
WEEK_NUMBER = 1         # Change this to the week number
# =======================================

class VoiceEmotionModule(ALModule):
    def __init__(self, name, session, csv_path):
        ALModule.__init__(self, name)
        self.session = session
        self.csv_path = csv_path

    def voice_emotion_callback(self, event_name, value, subscriber_identifier):
        try:
            matched_emotion_index = value[0][0]
            matched_emotion_level = value[0][1]
            emotion_levels = value[1]
            excitement_level = value[2]
            emotions = ["Unknown", "Calm", "Anger", "Joy", "Sorrow"]
            matched_emotion = emotions[matched_emotion_index] if matched_emotion_index < len(emotions) else "Unknown"
            
            # Create a timestamp in the same format as the conversation log
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Write to file with proper labels (Role/Content/Timestamp format)
            with open(self.csv_path, 'a') as f:
                f.write("{},Emotion,{},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f}\n".format(
                    current_time,
                    matched_emotion,
                    matched_emotion_level,
                    emotion_levels[0],  # calm
                    emotion_levels[1],  # anger
                    emotion_levels[2],  # joy
                    emotion_levels[3],  # sorrow
                    emotion_levels[4]   # laughter
                ))
                
            # Also print to terminal for feedback
            print("\n=== Voice Emotion Detected at {} ===".format(current_time))
            print("Dominant Emotion: {} (Level: {:.2f})".format(matched_emotion, matched_emotion_level))
            print("Calm: {:.4f}, Anger: {:.4f}, Joy: {:.4f}, Sorrow: {:.4f}, Laughter: {:.4f}".format(
                emotion_levels[0], emotion_levels[1], emotion_levels[2], emotion_levels[3], emotion_levels[4]
            ))
            print("Excitement Level: {:.4f}".format(excitement_level))
            
        except Exception as e:
            error_msg = "Error processing voice emotion callback: {}".format(e)
            print(error_msg)
            
            with open(self.csv_path, 'a') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("{},Error,{}\n".format(
                    current_time,
                    error_msg
                ))

def get_mood_data(session, csv_path):
    # Initialize services
    try:
        mood_service = session.service("ALMood")
        voice_emotion_service = session.service("ALVoiceEmotionAnalysis")
        memory_service = session.service("ALMemory")
        print("Services initialized successfully")
    except Exception as e:
        error_msg = "Failed to create proxies: {}".format(e)
        print(error_msg)
        with open(csv_path, 'a') as f:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("{},Error,{}\n".format(
                current_time,
                error_msg
            ))
        return

    # Subscribe to ALMood
    subscriber_name = "MoodSubscriber"
    operating_mode = "Active"
    
    try:
        if mood_service.subscribe(subscriber_name, operating_mode):
            log_msg = "Successfully subscribed to ALMood"
            print(log_msg)
            with open(csv_path, 'a') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("{},System,{}\n".format(
                    current_time,
                    log_msg
                ))
        else:
            log_msg = "Failed to subscribe to ALMood"
            print(log_msg)
            with open(csv_path, 'a') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("{},System,{}\n".format(
                    current_time,
                    log_msg
                ))
    except Exception as e:
        error_msg = "Error during ALMood subscription: {}".format(e)
        print(error_msg)
        with open(csv_path, 'a') as f:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("{},Error,{}\n".format(
                current_time,
                error_msg
            ))
        return

    # Create a voice emotion module for callbacks
    unique_name = "VoiceEmotionModule_" + str(random.randint(1, 10000))
    voice_emotion_module = VoiceEmotionModule(unique_name, session, csv_path)

    try:
        voice_emotion_service.subscribe(voice_emotion_module.getName())
        memory_service.subscribeToEvent("ALVoiceEmotionAnalysis/EmotionRecognized",
                                         voice_emotion_module.getName(),
                                         "voice_emotion_callback")
        log_msg = "Successfully subscribed to ALVoiceEmotionAnalysis"
        print(log_msg)
        with open(csv_path, 'a') as f:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("{},System,{}\n".format(
                current_time,
                log_msg
            ))
    except Exception as e:
        error_msg = "Error during ALVoiceEmotionAnalysis subscription: {}".format(e)
        print(error_msg)
        with open(csv_path, 'a') as f:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("{},Error,{}\n".format(
                current_time,
                error_msg
            ))

    try:
        log_msg = "Starting real-time emotion tracking (Press Ctrl+C to stop)"
        print(log_msg)
        with open(csv_path, 'a') as f:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("{},System,{}\n".format(
                current_time,
                log_msg
            ))
        
        # Main emotion detection loop
        sample_count = 0
        while True:
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # --- Facial Emotion Data ---
                person_state = mood_service.currentPersonState()
                
                if isinstance(person_state, dict):
                    # Get valence with confidence
                    valence_data = person_state.get("valence", {"value": "Unknown", "confidence": "Unknown"})
                    valence = valence_data.get("value", "Unknown")
                    
                    # Get attention with confidence
                    attention_data = person_state.get("attention", {"value": "Unknown", "confidence": "Unknown"})
                    attention = attention_data.get("value", "Unknown")
                    
                    # Get smile data
                    smile_data = person_state.get("smile", {"value": "Unknown", "confidence": "Unknown"})
                    smile = smile_data.get("value", "Unknown")
                    
                    # Get expressions
                    expressions = person_state.get("expressions", {})
                    expression_values = {}
                    for expr in ["happy", "surprised", "angry", "sad", "neutral"]:
                        expr_data = expressions.get(expr, {})
                        expression_values[expr] = expr_data.get("value", "Unknown")
                    
                    # Get ambient state
                    ambiance = mood_service.ambianceState()
                    ambient_calm = ambiance.get("calmLevel", "Unknown")
                    ambient_agitation = ambiance.get("agitationLevel", "Unknown")
                    
                    # Get emotional reaction
                    reaction = mood_service.getEmotionalReaction()
                    
                    # Print to console periodically
                    sample_count += 1
                    if sample_count % 5 == 0:
                        print("\n=== Facial Emotion Data at {} ===".format(current_time))
                        print("Valence (Mood): {}".format(valence))
                        print("Attention Level: {}".format(attention))
                        print("Smile Degree: {}".format(smile))
                        print("Facial Expressions:")
                        for expr, value in expression_values.items():
                            print("  - {}: {}".format(expr, value))
                        print("\n=== Environmental Emotion Data ===")
                        print("Calm Level: {}".format(ambient_calm))
                        print("Agitation Level: {}".format(ambient_agitation))
                        print("\n=== Emotional Reaction ===")
                        print("Detected Emotional Reaction: {}".format(reaction))
                    
                    # Write to CSV in Role,Content,Timestamp format
                    with open(csv_path, 'a') as f:
                        f.write("{},FacialEmotion,{},{},{},{},{},{},{},{},{},{}\n".format(
                            current_time,
                            valence,
                            attention,
                            smile,
                            expression_values["happy"],
                            expression_values["surprised"],
                            expression_values["angry"],
                            expression_values["sad"],
                            expression_values["neutral"],
                            ambient_calm,
                            ambient_agitation
                        ))
                
                else:
                    error_msg = "Unexpected data format from currentPersonState"
                    print(error_msg)
                    with open(csv_path, 'a') as f:
                        f.write("{},Error,{}\n".format(
                            current_time,
                            error_msg
                        ))
                
            except Exception as e:
                error_msg = "Error retrieving mood data: {}".format(e)
                print(error_msg)
                with open(csv_path, 'a') as f:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write("{},Error,{}\n".format(
                        current_time,
                        error_msg
                    ))
            
            # Sleep between samples
            time.sleep(5)
            
    except KeyboardInterrupt:
        log_msg = "Stopping real-time emotion tracking"
        print("\n" + log_msg)
        with open(csv_path, 'a') as f:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("{},System,{}\n".format(
                current_time,
                log_msg
            ))
    finally:
        # Clean up subscriptions
        try:
            mood_service.unsubscribe(subscriber_name)
            log_msg = "Successfully unsubscribed from ALMood"
            print(log_msg)
            with open(csv_path, 'a') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("{},System,{}\n".format(
                    current_time,
                    log_msg
                ))
        except Exception as e:
            error_msg = "Error unsubscribing from ALMood: {}".format(e)
            print(error_msg)
            with open(csv_path, 'a') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("{},Error,{}\n".format(
                    current_time,
                    error_msg
                ))
        
        try:
            voice_emotion_service.unsubscribe(voice_emotion_module.getName())
            memory_service.unsubscribeToEvent("ALVoiceEmotionAnalysis/EmotionRecognized",
                                               voice_emotion_module.getName())
            log_msg = "Successfully unsubscribed from ALVoiceEmotionAnalysis"
            print(log_msg)
            with open(csv_path, 'a') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("{},System,{}\n".format(
                    current_time,
                    log_msg
                ))
        except Exception as e:
            error_msg = "Error unsubscribing from ALVoiceEmotionAnalysis: {}".format(e)
            print(error_msg)
            with open(csv_path, 'a') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("{},Error,{}\n".format(
                    current_time,
                    error_msg
                ))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="128.237.236.27",
                        help="Robot IP address. Default: 128.237.236.27")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number. Default: 9559")
    args = parser.parse_args()
    
    # Create CSV filename based on participant and week number
    csv_filename = "participant_{}_week_{}_emotiondata.csv".format(PARTICIPANT_NUMBER, WEEK_NUMBER)
    
    # Create directory for CSV file if it doesn't exist
    csv_dir = os.path.dirname(csv_filename)
    if csv_dir and not os.path.exists(csv_dir):
        os.makedirs(csv_dir)
    
    # Initialize CSV file with header
    with open(csv_filename, 'w') as f:
        # Write descriptive header
        f.write("# Pepper Robot Emotion Tracking Data\n")
        f.write("# Participant: {}\n".format(PARTICIPANT_NUMBER))
        f.write("# Week: {}\n".format(WEEK_NUMBER))
        f.write("# Date: {}\n".format(datetime.now().strftime("%Y-%m-%d")))
        f.write("# Robot IP: {}\n".format(args.ip))
        f.write("# Port: {}\n".format(args.port))
        f.write("#\n")
        f.write("# CSV Format: Timestamp,DataType,Values...\n")
        f.write("# DataTypes:\n")
        f.write("#   System - System messages and status\n") 
        f.write("#   Error - Error messages\n")
        f.write("#   Emotion - Voice emotion data (format: Emotion,DominantEmotion,EmotionLevel,Calm,Anger,Joy,Sorrow,Laughter)\n")
        f.write("#   FacialEmotion - Facial emotion data (format: FacialEmotion,Valence,Attention,Smile,Happy,Surprised,Angry,Sad,Neutral,AmbientCalm,AmbientAgitation)\n")
        f.write("#\n")
        
        print("Created CSV file: {}".format(csv_filename))
        print("Header information includes field descriptions")
    
    print("Connecting to Pepper at {}:{}...".format(args.ip, args.port))
    session = qi.Session()

    try:
        session.connect("tcp://" + args.ip + ":" + str(args.port))
        print("Successfully connected to Pepper")
    except RuntimeError:
        error_msg = "Can't connect to Naoqi at ip {} on port {}.".format(args.ip, args.port)
        print(error_msg)
        with open(csv_filename, 'a') as f:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("{},Error,{}\n".format(
                current_time,
                error_msg
            ))
        sys.exit(1)
    
    # Create broker
    print("Creating ALBroker...")
    myBroker = ALBroker("myBroker", "0.0.0.0", 0, args.ip, args.port)
    
    # Start mood data collection
    print("Starting emotion data collection...")
    with open(csv_filename, 'a') as f:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write("{},System,Starting emotion data collection\n".format(current_time))
    
    get_mood_data(session, csv_filename)