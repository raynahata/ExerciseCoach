#!/usr/bin/env python3
import rospy
import rosbag
import numpy as np
import matplotlib.pyplot as plt
from config_computer import *
from ExerciseController_computer import ExerciseController
from datetime import datetime
from pytz import timezone
import logging
import time
import pickle
from std_msgs.msg import Int32
from pynput import keyboard

#Parameters
SET_LENGTH = 20
REST_TIME = 40
#EXERCISE_LIST = ['bicep_curls'] #comment out before actual sessions
EXERCISE_LIST = ['bicep_curls', 'bicep_curls', 'lateral_raises', 'lateral_raises']

#Change at beginning of study - make sure to change in adaptive_controller.py as well
PARTICIPANT_ID = '0'
RESTING_HR = 97
AGE = 26

#Change at beginning of each round
ROBOT_STYLE = 6 #1 is firm, 3 is encouraging, 5 is adaptive. 6 is social
ROUND_NUM = 1  #0 is intro

MAX_HR = 220-AGE

#Initialize ROS node
rospy.init_node('study_session', anonymous=True)
rate = rospy.Rate(10)
set_pub = rospy.Publisher("set_performance", Int32, queue_size=10)

#Start log file
log_filename = 'Participant_{}_Style_{}_Round_{}_{}.log'.format(PARTICIPANT_ID, ROBOT_STYLE, ROUND_NUM, datetime.now().strftime("%Y-%m-%d--%H-%M-%S"))
data_filename = 'Participant_{}_Style_{}_Round_{}_{}.pickle'.format(PARTICIPANT_ID, ROBOT_STYLE, ROUND_NUM, datetime.now().strftime("%Y-%m-%d--%H-%M-%S"))

#Initialize evaluation object
controller = ExerciseController(False, log_filename, ROBOT_STYLE, RESTING_HR, MAX_HR, PARTICIPANT_ID)
rospy.sleep(2)

rospy.sleep(4)

intake_heart_rates = []
def intake_heart_rate_callback(msg):
    intake_heart_rates.append(msg.data)
    

if ROUND_NUM == 0:
    heart_rate_sub = rospy.Subscriber("/heart_rate", Int32, intake_heart_rate_callback, queue_size=3000)

    controller.logger.info('Resting Heart Rate Computed: {}'.format(np.mean(intake_heart_rates)))

if ROUND_NUM > 0:
    input("Press Enter to to start exercise session...")
    controller.message('Let us start Round {} now. Please stand in the blue square and pick up the dumbbells if you want to use them'.format(ROUND_NUM))
    input("Press Enter to to start exercise session...")

    #For each exercise
    for set_num, exercise_name in enumerate(EXERCISE_LIST):
                
        #Start a new set
        controller.start_new_set(exercise_name, set_num+1, len(EXERCISE_LIST))
        
        controller.logger.info('-------------------Recording!')
        start_message = False
        halfway_message = False

        #Lower arm all the way down
        controller.move_right_arm('halfway', 'sides')
        
        inittime = datetime.now(timezone('EST'))
        
        #Stop between minimum and maximum time and minimum reps
        while (datetime.now(timezone('EST')) - inittime).total_seconds() < SET_LENGTH:        
                    
            #Robot says starting set
            if not start_message:
                robot_message = "Start %s now" % (exercise_name.replace("_", " " ))
                controller.message(robot_message)
                start_message = True

            controller.flag = True

            if (datetime.now(timezone('EST')) - inittime).total_seconds() > SET_LENGTH/2 and not halfway_message:
                robot_message = "You are halfway"
                controller.message(robot_message)
                halfway_message = True 

            if (datetime.now(timezone('EST')) - inittime).total_seconds() > SET_LENGTH:
                break 

        controller.flag = False
        controller.logger.info('-------------------Done with exercise')

        robot_message = "Almost done."
        controller.message(robot_message)
        rospy.sleep(3)

        rest_start = datetime.now(timezone('EST'))

        robot_message = "Time to rest."
        controller.message(robot_message)
        controller.change_expression('smile', controller.start_set_smile, 4)

        #Raise arm all the way up
        controller.move_right_arm('sides', 'up')
        
        if set_num + 1 < len(EXERCISE_LIST):
            halfway_message = False
            while (datetime.now(timezone('EST')) - rest_start).total_seconds() < REST_TIME:
                
                #Print halfway done with rest here
                if (datetime.now(timezone('EST')) - rest_start).total_seconds() > REST_TIME/2 and not halfway_message:
                    halfway_message = True
                    robot_message = "Rest for {} more seconds.".format(int(REST_TIME/2))
                    controller.message(robot_message)
        else:
            robot_message = "Round complete. Please take a seat in the chair and complete a survey about this round on the laptop next to you."
            controller.message(robot_message)

    controller.change_expression('smile', controller.start_set_smile, 4)

    if controller.robot_style == 5:
        controller.process.stdin.write('exit\n')
        controller.process.stdin.flush()

        if controller.process.stdin:
            controller.process.stdin.close()
        if controller.process.stdout:
            controller.process.stdout.close()
        # controller.process.wait()

    data = {'angles': controller.angles, 'peaks': controller.peaks, 'feedback': controller.feedback, 'times': controller.times, 'exercise_names': controller.exercise_name_list, 'all_hr': controller.all_heart_rates, 'heart_rates': controller.heart_rates, 'hrr': controller.hrr, 'actions': controller.actions, 'context': controller.contexts, 'rewards': controller.rewards}
    
    dbfile = open('/home/roshni/quori_files/quori_ros/src/quori_exercises/saved_data/{}'.format(data_filename), 'ab')

    pickle.dump(data, dbfile)                    
    dbfile.close()

    controller.logger.info('Saved file {}'.format(data_filename))

controller.logger.handlers.clear()
logging.shutdown()
print('Done!')

controller.plot_angles()

plt.show()