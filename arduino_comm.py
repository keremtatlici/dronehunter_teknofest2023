import serial.tools.list_ports
import time

def find_arduino_comport():
    port= None
    ports = serial.tools.list_ports.comports()
    for ports, desc, hwid in ports:
        device_name = desc.split(' ')[0]
        print(device_name)
        if device_name.__eq__("Arduino") :
            port = ports
    return port

def connect_to_arduino():
    """
    port: String -> Port bilgisi
    return: serial Object -> arduinonun bağlantı değişkeni
    """
    return serial.Serial(port="/dev/ttyUSB0", baudrate=9600, timeout=.1)

def send_message(arduino, message, delay=3.000):
    """
    arduino : Serial Object -> arduinonun bağlantı değişkeni
    message: String -> gönderilecek mesaj
    return : None
    """
    arduino.write(message.encode())
    time.sleep(delay)

