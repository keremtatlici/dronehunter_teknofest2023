# This is server code to send video frames over UDP
import cv2, imutils, socket
import numpy as np
import time
import base64
import threading
import sys
import keyboard
import database as db
from time import sleep
import math
import json
import pickle

def temp_socket():
    BUFF_SIZE = 65536
    client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)
    #client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #host_name = socket.gethostname()
    #db.ip = socket.gethostbyname(host_name)
    print(db.gazebo_ip)
    port = 9945
    message = b'Hello'

    client_socket.sendto(message,(db.gazebo_ip,port))
    fps,st,frames_to_count,cnt = (0,0,20,0)

    while True:
        packet,_ = client_socket.recvfrom(BUFF_SIZE)
        #print("MESAJ ALINDII!!!!!!!!!!!!!!!!!!!!!!!!")
        data = base64.b64decode(packet,' /')
        npdata = np.fromstring(data,dtype=np.uint8)
        
        frame = cv2.imdecode(npdata,1)

        db.liveframe=frame
        sleep(0.05)

class thread_with_trace(threading.Thread):
  def __init__(self, *args, **keywords):
    threading.Thread.__init__(self, *args, **keywords)
    self.killed = False
 
  def start(self):
    self.__run_backup = self.run
    self.run = self.__run     
    threading.Thread.start(self)
 
  def __run(self):
    sys.settrace(self.globaltrace)
    self.__run_backup()
    self.run = self.__run_backup
 
  def globaltrace(self, frame, event, arg):
    if event == 'call':
      return self.localtrace
    else:
      return None
 
  def localtrace(self, frame, event, arg):
    if self.killed:
      if event == 'line':
        raise SystemExit()
    return self.localtrace
 
  def kill(self):
    self.killed = True
 
def func():
  while True:
    print('thread running')

def fire():
    portFire = 9948
    server_socketFire = socket.socket()  # FIRE 
    server_socketFire.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 3)
    server_socketFire.bind((db.ip, portFire)) 
    server_socketFire.listen(2)
    connFire, addressFire = server_socketFire.accept()
    print("Connection from: " + str(addressFire))
    while True:
        data = connFire.recv(1024).decode()
        if data == "fire is open":
          print("ATES SERBEST")
        elif data == "fire is not permitted":
          print("ATESI DURDUR")  
          
def mission():
    portMission = 9947
    server_socketMission = socket.socket()  # MISSION
    server_socketMission.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 3)
    server_socketMission.bind((db.ip, portMission)) 
    server_socketMission.listen(2)
    connMission, addressMission = server_socketMission.accept()
    print("Connection from: " + str(addressMission))
    while True:
        data = connMission.recv(1024).decode()
        if data == "startMission":
          if db.isMissionStarted == False:
             print("GOREV BASLATILDI")
             db.isMissionStarted = True

        elif data == "endMission":
          if db.isMissionStarted == True:
             print("GOREV DURDURULDU")  
             db.isMissionStarted = False
        
def telemetrik():

    portTelemetrik = 9946
    server_socketTelemetrik = socket.socket()  # TELEMETRIK
    server_socketTelemetrik.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 2)
    server_socketTelemetrik.bind((db.ip, portTelemetrik)) 
    server_socketTelemetrik.listen(2)
    connTelemetrik, addressTelemetrik = server_socketTelemetrik.accept()
    print("Connection from: " + str(addressTelemetrik))
    while True:
      telemetry_packet = { 
        "la": float(db.vehicle.location.global_relative_frame.lat), #latitude
        "lo": float(db.vehicle.location.global_relative_frame.lon), #longtitude
        "al": float(db.vehicle.location.global_relative_frame.alt), #altitude
        "pi": float(math.degrees(db.vehicle.attitude.pitch)),       #pitch 
        "ro": float(math.degrees(db.vehicle.attitude.roll)),        #roll
        "ya": float(math.degrees(db.vehicle.attitude.yaw)),         #yaw
        "av": float(db.vehicle.airspeed),                           #airspeed
        "gv": float(db.vehicle.groundspeed),                        #groundspeed
        "bt": float(db.vehicle.battery.level),                      #battery
      }

      data = json.dumps(telemetry_packet)
      #print(data)
      #print(type(data))
      data = pickle.dumps(data)
      connTelemetrik.send(data)  
      sleep(1)

def frame():
  portFrame = 9945
  portFrame2 = 9955
  BUFF_SIZE = 65536

  server_socketFrame = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  server_socketFrame.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)

  server_socketFrame2 = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  server_socketFrame2.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)

  socket_address = (db.ip,portFrame)
  server_socketFrame.bind(socket_address)

  socket_address2 = (db.ip,portFrame2)
  server_socketFrame2.bind(socket_address2)

  msg,client_addr = server_socketFrame.recvfrom(BUFF_SIZE)
  msg2,client_addr2 = server_socketFrame2.recvfrom(BUFF_SIZE)

  while True:
    if db.liveframe is not None :
      frame = db.liveframe
      frame = imutils.resize(frame,width=400)
      encoded,buffer = cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,60])

      buffer1 = buffer[:len(buffer)]
      message = base64.b64encode(buffer1)

      buffer2 = buffer[len(buffer):]
      message2 = base64.b64encode(buffer2)

      server_socketFrame.sendto(message, client_addr)
      server_socketFrame2.sendto(message2, client_addr2)

"""def frame():
  portFrame = 9945
  BUFF_SIZE = 65536
  server_socketFrame = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  server_socketFrame.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)
  socket_address = (db.ip,portFrame)
  server_socketFrame.bind(socket_address)
  msg,client_addr = server_socketFrame.recvfrom(BUFF_SIZE)
  while True:
    if db.liveframe is not None :
      time.sleep(0.01)
      encoded,buffer = cv2.imencode('.jpg',db.liveframe,[cv2.IMWRITE_JPEG_QUALITY,50])
      message = base64.b64encode(buffer)
      server_socketFrame.sendto(message, client_addr)"""
      
db.telemetry_socket = thread_with_trace(target = telemetrik)
db.liveframe_socket = thread_with_trace(target = frame)
db.missionstart_socket = thread_with_trace(target = mission)
db.firepermission_socket = thread_with_trace(target = fire)

