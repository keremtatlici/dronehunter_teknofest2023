import database as db
import socket
import cv2
import numpy as np
import time
import imutils
import pickle
import struct

## bu kodun bulundugu ayni yolda database.py diye bir script var bende, sende bos bir database.py scripti olustur.
## database.py scriptinde ip = "192.168..." seklinde ip girisi yapman lazim. Gerekli importlari ekleyip gereksiz importlari sil.


def mission_socket():
    ## BURAYI Ben ayarladim portunu felan degistirebilirsin kendine gore.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((db.ip, 9999))
    server.listen()
    client, client_adress = server.accept()

    while True:
        message =client.recv(1024)
        print(message)
        time.sleep(1)
        message = message.decode("ascii")
        if message == "missionstart":
            db.is_mission=True
            print("Yerden emir geldi Görev BASLATILDI!!")
        elif message == "missionend":
            db.is_mission=False
            print("Yerden emir geldi Görev DURDURULDU!!")
        else:
            print("yerden gelen gorev emri hatali!!!")
            pass
            

def liveframe_socket():
    ## BURAYI SAMIR SEN DOLDUR db.liveframe 'den gelen frame'i socket ile gonder. Asagidaki kod gecen seneden kalma kod.
    # silip bastan yazabilirsin ama while true yapman lazim.db.liveframe kameradan gelen guncel frame'i tutacak.


    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    port = 9998
    socket_address = (db.ip,port)
    server.bind(socket_address)
    server.listen(5)
    client, address = server.accept()

    while True:
        if db.liveframe is not None:
            time.sleep(0.100) 
            frame = db.liveframe.frame
            width= db.liveframe.width
            frame = imutils.resize(frame, width=320)
            a = pickle.dumps(frame)
            message = struct.pack("Q",len(a))+a
            print("liveframe göndermeye çalışıyor ..")
            client.sendall(message)            
            print(frame.shape)


def atis_serbest_socket():
    ## BURAYI SAMIR SEN DOLDUR
    #BURADA ATIS SERBESTI GELDI MI KONTROLU YAPILACAK ATIS SERBEST MESAJI GELDI ISE
    #db.is_atis_serbest = True YAPILACAK
    #ATISYASAK EMRI GELIRSE db.is_atis_serbest = False YAPILACAK

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((db.ip, 9996))
    server.listen()
    client, client_adress = server.accept()

    while True:
        if db.normalframe is not None:
            pass

def telemetri_socket():

    ## BURAYI SAMIR SEN DOLDUR db.telemetri paketi her saniye veya saniyeden daha kisa bir surede guncelleniyor.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((db.ip, 9994))
    server.listen()
    client, client_adress = server.accept()   

    while True:
        if db.telemetri is not None:
            pass 