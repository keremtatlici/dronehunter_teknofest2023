# This is server code to send video frames over UDP
import cv2, imutils, socket
import numpy as np
import time
import base64
import threading
import sys
import keyboard
import database as db


def temp_socket():
    BUFF_SIZE = 65536
    client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)
    #client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #host_name = socket.gethostname()
    #db.ip = socket.gethostbyname(host_name)
    db.ip =  '192.168.1.103'
    print(db.ip)
    port = 9945
    message = b'Hello'

    client_socket.sendto(message,(db.ip,port))
    fps,st,frames_to_count,cnt = (0,0,20,0)

    while True:
        packet,_ = client_socket.recvfrom(BUFF_SIZE)
        data = base64.b64decode(packet,' /')
        npdata = np.fromstring(data,dtype=np.uint8)
        
        frame = cv2.imdecode(npdata,1)

        db.liveframe=frame

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
        data = connTelemetrik.recv(1024).decode()
        for key, value in db.data.items():
            data = key + " " + value
            connTelemetrik.send(data.encode()) 
      
def frame():
  portFrame = 9945
  BUFF_SIZE = 65536
  server_socketFrame = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  server_socketFrame.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)
  socket_address = (db.ip,portFrame)
  server_socketFrame.bind(socket_address)
  msg,client_addr = server_socketFrame.recvfrom(BUFF_SIZE)
  while True:
    if db.liveframe is not None :
      encoded,buffer = cv2.imencode('.jpg',db.liveframe,[cv2.IMWRITE_JPEG_QUALITY,80])
      message = base64.b64encode(buffer)
      server_socketFrame.sendto(message, client_addr)
      
db.telemetry_socket = thread_with_trace(target = telemetrik)
db.liveframe_socket = thread_with_trace(target = frame)
db.missionstart_socket = thread_with_trace(target = mission)
db.firepermission_socket = thread_with_trace(target = fire)

