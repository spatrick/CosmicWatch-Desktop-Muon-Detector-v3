# This script requires two libraries:
# pip install tornado
# pip install pyserial

import serial 
import time
import glob
import sys
import os
import os.path
import signal
from datetime import datetime
from multiprocessing import Process

import numpy as np
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import socket
import multiprocessing
import math
import random
import thread
import serial 
import time

'''
This is a Websocket server that forwards signals from the detector to any client connected.
It requires Tornado python library to work properly.
Please run `pip install tornado` with python of version 2.7.9 or greater to install tornado.
Run it with `python detector-server.py`
Written by Pawel Przewlocki (pawel.przewlocki@ncbj.gov.pl).
Based on http://fabacademy.org/archives/2015/doc/WebSocketConsole.html
''' 

def print_help1():
    print('\n===================== HELP =======================')
    print('This code looks through the serial ports. ')
    print('You can select multiple ports with by separating the port number with commas.')
    print('You must select which port contains the Arduino.\n')
    print('If you have problems, check the following:')
    print('1. Is your Arduino connected to the serial USB port?\n')
    print('2. Check that you have the correct drivers installed:\n')
    print('\tMacOS: CH340g driver (try: https://github.com/adrianmihalko/ch340g-ch34g-ch34x-mac-os-x-driver)')
    print('\tWindows: no dirver needed')
    print('\tLinux: no driver needed')


clients = [] ## list of clients connected
queue = multiprocessing.Queue() #queue for events forwarded from the device

class DataCollectionProcess(multiprocessing.Process):
    def __init__(self, queue):
        #multiprocessing.Process.__init__(self)
        self.queue = queue
        self.comport = serial.Serial(port_name_list[0]) # open the COM Port
        self.comport.baudrate = 115200          # set Baud rate
        self.comport.bytesize = 8             # Number of data bits = 8
        self.comport.parity   = 'N'           # No parity
        self.comport.stopbits = 1 

    def close(self):
        self.comport.close()
        
    def nextTime(self, rate):
        return -math.log(1.0 - random.random()) / rate

def RUN(bg):
    print('Running...')
    while True:
        data = bg.comport.readline()
        bg.queue.put(str(datetime.now())+" "+data)
    
class WSHandler(tornado.websocket.WebSocketHandler):
    def __init__ (self, application, request, **kwargs):
        super(WSHandler, self).__init__(application, request, **kwargs)
        self.sending = False

    def open(self):
        print('New connection opened from ' + self.request.remote_ip)
        clients.append(self)
        print('%d clients connected' % len(clients))
    def on_message(self, message):
        print('message received:  %s' % message)
        if message == 'StartData':
            self.sending = True
        if message == 'StopData':
            self.sending = False
 
    def on_close(self):
        self.sending = False
        clients.remove(self)
        print('Connection closed from ' + self.request.remote_ip)
        print('%d clients connected' % len(clients))
 
    def check_origin(self, origin):
        return True

def checkQueue():
    while not queue.empty():
        message = queue.get()
        ##sys.stdout.write('#')
        for client in clients:
            if client.sending:
                client.write_message(message)
 

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    ComPort.close()     
    file.close() 
    sys.exit(0)

def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
        sys.exit(0)
    result = []
    for port in ports:
        try: 
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

#If the Arduino is not recognized by your MAC, make sure you have
#   installed the drivers for the Arduino (CH340g driver). Windows and Linux don't need it.

print('\n             Welcome to:   ')
print('CosmicWatch: The Desktop Muon Detector\n')

print("What would you like to do:")
print("[1] Record data on the computer")
print("[2] Copy data files from SD card to your computer")
print("[3] Remove files from SD card")
print("[4] Connect to server: www.cosmicwatch.lns.mit.edu")
print("[h] Help")

mode = str(raw_input("\nSelected operation: "))

if mode == 'h':
    print_help1()
    sys.exit()

else:
    mode = int(mode)
    if mode not in [1,2,3,4]:
        print('-- Error --')
        print('Invalid selection')
        print('Exiting...')
        sys.exit()

t1 = time.time()
port_list = serial_ports()
t2 = time.time()
if (t2-t1)>2:
    print('Listing ports is taking unusually long. Try disabling your Bluetooth.')

print('Available serial ports:')
for i in range(len(port_list)):
    print('['+str(i+1)+'] ' + str(port_list[i]))
print('[h] help\n')

ArduinoPort = raw_input("Selected Arduino port: ")

ArduinoPort = ArduinoPort.split(',')
nDetectors = len(ArduinoPort)

if mode in [2,3,4]:
    if len(ArduinoPort) > 1:
        print('--- Error ---')
        print('You selected multiple detectors.')
        print('This options is only compatible when recording to the computer.')
        print('Exiting...')
        sys.exit()

port_name_list = []

for i in range(len(ArduinoPort)):
	port_name_list.append(str(port_list[int(ArduinoPort[i])-1]))

if ArduinoPort == 'h':
    print_help1()
    sys.exit()

print("The selected port(s) is(are): ")
for i in range(nDetectors):	 
	print('\t['+str(ArduinoPort[i])+']' +port_name_list[i])

if mode == 1:
    cwd = os.getcwd()
    fname = raw_input("Enter file name (default: "+cwd+"/CW_data.txt):")
    detector_name_list = []
    if fname == '':
        fname = cwd+"/CW_data.txt"

    print('Saving data to: '+fname)
    ComPort_list = np.ones(nDetectors)

    for i in range(nDetectors):
        s = serial.Serial(str(port_name_list[i]))
        #s = signal.signal(signal.SIGINT, signal_handler)
        #serial.Serial(str(port_name_list[i])).write("reset") 
        #s.setDTR(True)
        print("Reseting detector...")
        #time.sleep(4)
        #s.flushInput()
        #s.setDTR(False)
        signal.signal(signal.SIGINT, signal_handler)
        globals()['Det%s' % str(i)] = serial.Serial(str(port_name_list[i]))
        globals()['Det%s' % str(i)].baudrate = 115200    
        globals()['Det%s' % str(i)].bytesize = 8             # Number of data bits = 8
        globals()['Det%s' % str(i)].parity   = 'N'           # No parity
        globals()['Det%s' % str(i)].stopbits = 1 

        time.sleep(1)
        #globals()['Det%s' % str(i)].write('write')  
        #globals()['Det%s' % str(i)].write("reset")
        #counter = 0

        #headers = []
        '''
        while (True):
            header = globals()['Det%s' % str(i)].readline()     # Wait and read data 
            if "###" in header:
                headers.append(header)
            if "#" not in header:
                break
            if 'Device ID: ' in header:
                det_name = header.split('Device ID: ')[-1]

        detector_name_list.append(det_name)    # Wait and read data 
        '''

    file = open(fname, "w",0)
    #for i in range(len(headers)):
    #    file.write(headers[i])
    
    #string_of_names = ''
    print("\n-- Detector Names --")
    #print(detector_name_list)
    '''
    for i in range(len(detector_name_list)):
            print(detector_name_list[i])
            if '\xff' in detector_name_list[i] or '?' in detector_name_list[i] :
                    print('--- Error ---')
                    print('You should name your CosmicWatch Detector first.')
                    print('Simply change the DetName variable in the Naming.ino script,')
                    print('and upload the code to your Arduino.')
                    print('Exiting ...')
    '''
    print("\nTaking data ...")
    print("Press ctl+c to terminate process")
    '''
    if nDetectors>1:
            for i in range(nDetectors):
                    string_of_names += detector_name_list[i] +', '
    else:
            string_of_names+=detector_name_list[0]
    '''
    while True:
        for i in range(nDetectors):
            if globals()['Det%s' % str(i)].inWaiting():
                data = globals()['Det%s' % str(i)].readline().replace('\r\n','')    # Wait and read data 
                data = data.split('\t')
                ti = str(datetime.now()).split(" ")
                data[1] = ti[-1]
                data[2] = ti[0].replace('-','/')
                #file.write(str(datetime.now())+" "+data+" "+detector_name_list[i]+'\n')
                for j in range(len(data)):
                    file.write(data[j]+'\t')
                #file.write("\t"+detector_name_list[i]+'\n')
                file.write("\n")
                globals()['Det%s' % str(i)].write('got-it') 

    for i in range(nDetectors):
            globals()['Det%s' % str(i)].close()     
    file.close()  



