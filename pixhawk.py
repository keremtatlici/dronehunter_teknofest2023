from time import sleep
from dronekit import connect
import math
import matplotlib.path as mplpath
import numpy as np
from dronekit import LocationGlobalRelative
import database as db

#vehicle = connect('/dev/ttyTHS1',wait_ready = True)
#vehicle.mode = "GUIDED"

def set_attitude_target(vehicle ,roll_angle = 0.0, pitch_angle = 0.0, yaw_angle = None,yaw_rate=0.0,use_yaw_rate=False,thrust= 0.5):
    if yaw_angle is None:
        yaw_angle = vehicle.attitude.yaw

    msg = vehicle.message_factory.set_attitude_target_encode(
        0,
        1,
        1,
        0b00000000 if use_yaw_rate else 0b00000100,
        to_quaternion(roll_angle,pitch_angle,yaw_angle),
        0,
        0,
        math.radians(yaw_rate),
        thrust
    )
    vehicle.send_mavlink(msg)
    
def setrangenumber(value,h,w, attitude,sensity):
    if attitude == True:
        old_value = value
        old_min = -(w/2)
        old_max = w/2
        new_min = 0
        new_max = sensity*100
        new_value = ( (old_value - old_min) / (old_max - old_min) ) * (new_max - new_min) + new_min
    if attitude == False:
        old_value = value
        old_min = -(h/2)
        old_max = h/2
        new_min = 0
        new_max = sensity*100
        new_value = ( (old_value - old_min) / (old_max - old_min) ) * (new_max - new_min) + new_min
    return new_value
    
def icerde_miyiz(lat,lon):
    myposition= (lat,lon)
    polypath = mplpath.Path(np.array([[40.2299,29.0081],[40.2308236,29.0040779],[40.2333136,29.0038848],[40.2334,29.0082]]))
    
    return polypath.contains_point(myposition)


def followtodrone(frame_width, frame_height, center_x, center_y,bbox_width, bbox_height, vehicle):
    if bbox_width+bbox_height >1:
            print("OBJECT DETECTİON VAR VE GUİDED")
            if vehicle.mode != 'GUIDED':
                vehicle.mode='GUIDED'

            roll = int((center_x-(frame_width/2))/10)
            pitch = int(((-center_y+(frame_height/2)))/30)
            print(f'roll: {roll}, pitch: {pitch}')
            #pitch = 0.0
            #print('###############################################################################################')
            set_attitude_target(vehicle, roll_angle = roll , pitch_angle = pitch , yaw_angle = None , yaw_rate = 0.0 , use_yaw_rate= False , thrust = 0.5 )
        
    elif vehicle.mode != 'AUTO':
        vehicle.mode = 'AUTO'

def followto(frame_width, frame_height, center_x, center_y,bbox_width, bbox_height, vehicle, hedef_gps=None, roll_sensity = 1, pitch_sensity = 1):
    #orta_konum = (40.2323, 29.0852)
    #orta_konum = LocationGlobalRelative(40.2323, 29.0052, vehicle.location.global_relative_frame.alt)
    #print(orta_konum)
    #print(vehicle.mode)
    #print(f"kanal 5:{vehicle.channels['5']}")
    #print(f"kanal 6:{vehicle.channels['6']}")
    #print(f"kanal 7:{vehicle.channels['7']}")
    #print(f"kanal 8:{vehicle.channels['8']}")
    #sleep(0.2) param set AFS_TERMINATE 0
    #print(vehicle.last_heartbeat)
    # if vehicle.channels['8']>1500 and vehicle.channels['6'] > 1700:
    #     #print('vehicle channel 10 > 1500 ve vehicle channel 6 >1700')
    #     if vehicle.mode != 'GUIDED':
    #             vehicle.mode='GUIDED'
    #     orta_konuma_git(vehicle)
    #     return

    # if vehicle.channels['7']>1500:
    #         #print('vehicle channel 7 > 1500')
    #         #print('#####################################################')
    #         #print(vehicle.channels['7'])
        
    #         vehicle.commands.next=5
    #         #print(vehicle.commands.next)
    #         vehicle.commands.upload()
            
    #if icerde_miyiz(vehicle.location.global_relative_frame.lat, vehicle.location.global_relative_frame.lon):
        #print("icerdemiyiz")
        
        #Eğer sınırların içerisindeysek buraya girecek
        if bbox_width+bbox_height >1 and vehicle.channels['6'] > 1700:
            print("OBJECT DETECTİON VAR VE GUİDED")
            if vehicle.mode != 'GUIDED':
                vehicle.mode='GUIDED'

            roll = int((center_x-(frame_width/2))/10)
            pitch = int(((-center_y+(frame_height/2)))/30)
            #pitch = 0.0
            #print('###############################################################################################')
            set_attitude_target(vehicle, roll_angle = roll , pitch_angle = pitch , yaw_angle = None , yaw_rate = 0.0 , use_yaw_rate= False , thrust = 0.5 )
        
        elif vehicle.mode != 'AUTO':
            vehicle.mode = 'AUTO'
            

# channel 7 1500 üzeri oto modda         
    # else:
    #     orta_konuma_git(vehicle)
    #     #Eğer sınır dışındaysak buraya girecek
    #     if vehicle.channels['6'] > 1700:
    #         if vehicle.mode != 'GUIDED':
    #             vehicle.mode='GUIDED'
    #     elif vehicle.mode != 'MANUAL' and vehicle.channels['6'] <= 1400:
    #         vehicle.mode = 'MANUAL'
    #     elif vehicle.mode != 'AUTO' and vehicle.channels['6']>1400 and vehicle.channels['6'] < 1700:
    #         vehicle.mode = 'AUTO' 
        

def orta_konuma_git(vehicle):
    #print('methoda girdi!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    orta_konum = LocationGlobalRelative(40.2319048, 29.0064812, vehicle.location.global_relative_frame.alt)
    vehicle.simple_goto(orta_konum)   

def to_quaternion(roll = 0.0, pitch = 0.0, yaw = 0.0):
    """
    Convert degrees to quaternions
    """
    t0 = math.cos(math.radians(yaw * 0.5))
    t1 = math.sin(math.radians(yaw * 0.5))
    t2 = math.cos(math.radians(roll * 0.5))
    t3 = math.sin(math.radians(roll * 0.5))
    t4 = math.cos(math.radians(pitch * 0.5))
    t5 = math.sin(math.radians(pitch * 0.5))

    w = t0 * t2 * t4 + t1 * t3 * t5
    x = t0 * t3 * t4 - t1 * t2 * t5
    y = t0 * t2 * t5 + t1 * t3 * t4
    z = t1 * t2 * t4 - t0 * t3 * t5

    return [w, x, y, z]
       
    
    
    
