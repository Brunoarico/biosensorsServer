'''operation mode'''
debug_mock = True
logmode = True

'''python OSC library'''
from pythonosc import osc_message_builder
from pythonosc import osc_bundle_builder
from pythonosc import udp_client

'''Neurosky library'''
import mindwavemobile.MindwaveDataPoints as dp
from mindwavemobile.MindwaveDataPointReader import MindwaveDataPointReader

'''Native Librarys'''
from random import randrange
import threading
import queue
import time
import datetime as dt

'''IMU sensor library'''
if(not debug_mock): import FaBo9Axis_MPU9250
else: print("IMU Sensor mocked")

'''HeartBeat sensor library'''
if(not debug_mock): import max30102
else: print("Heartbeat Sensor mocked")

'''queue control size'''
EEG_QUEUE_MAXSIZE = 100
HEART_QUEUE_MAXSIZE = 100
IMU_QUEUE_MAXSIZE = 100

IP ="192.168.0.202"                       #change
PORT = 5005                           #change
EEG_addr = 'C4:64:E3:E7:B6:A9'        #change


class SensorMSG():
    def __init__(self, EEG = True, IMU = True, HEART = True):
        self.EEG_addr = EEG_addr
        self.EEG_queue = queue.Queue(maxsize=EEG_QUEUE_MAXSIZE)
        self.HEART_queue = queue.Queue(maxsize=HEART_QUEUE_MAXSIZE)
        self.IMU_queue = queue.Queue(maxsize=IMU_QUEUE_MAXSIZE)
        if(logmode):
            self.log_file = open("logfile.log","a")
            self.log_file.write(dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S\n"))

        '''Enable sensors to work'''
        self.EEG_enable = EEG
        self.HEART_enable = HEART
        self.IMU_enable = IMU

        '''connection status'''
        self.EEG_status = False
        self.HEART_status = False
        self.IMU_status = False

        '''control execuion flags'''
        self.EEG_running = 0
        self.HEART_running = 0
        self.IMU_running = 0
        self.SENDER_running = 0

        '''last time update sensor'''
        self.EEG_t_last = dt.datetime.now()
        self.HEART_t_last = dt.datetime.now()
        self.IMU_t_last = dt.datetime.now()

        if(EEG): self.connect_EEG(self.EEG_addr)
        if(IMU): self.connect_IMU()
        if(HEART): self.connect_HEART()

    def print_log(self, str):
        print(str)
        self.log_file.write(dt.datetime.now().strftime("%H:%M:%S: ") + str + "\n")

    def connect_EEG(self, addr):
        self.print_log("[+] Try to connect")
        self.mindwaveDataPointReader = MindwaveDataPointReader(addr)
        while True:
            try:
                self.mindwaveDataPointReader.start()
                time.sleep(2)
                if (self.mindwaveDataPointReader.isConnected()):
                    self.print_log("[+] Connected")
                    self.EEG_status = True
                    return self.EEG_status
            except:
                self.print_log("[-] Fail Connection")
                time.sleep(2)
                self.print_log("[+] retry...")

    def get_EEG(self):
        if(self.EEG_status):
            self.print_log("[+] getting EEG values: Status: " + str(self.EEG_status) +" Running: "+ str(self.EEG_running))
            dict = {'Meditation':0, 'Attention':0, 'delta':'0', 'theta':'0', 'lowAlpha':'0', 'highAlpha':'0', 'lowBeta':'0', "highBeta":'0', 'lowGamma':'0', 'midGamma':'0','PoorSignalLevel':0}
            self.med_value = 0
            self.at_value = 0
            self.signal = 0
            while(self.EEG_running):
                dataPoint = self.mindwaveDataPointReader.readNextDataPoint()
                if(dataPoint.__class__ is dp.PoorSignalLevelDataPoint):
                    poorSignalLevel = dataPoint.dict()
                    dict.update(poorSignalLevel)
                elif (dataPoint.__class__ is dp.AttentionDataPoint):
                    attention = dataPoint.dict()
                    dict.update(attention)
                elif (dataPoint.__class__ is dp.MeditationDataPoint):
                    meditation = dataPoint.dict()
                    dict.update(meditation)
                elif (dataPoint.__class__ is dp.EEGPowersDataPoint):
                    eegPowers = dataPoint.dict()
                    dict.update(eegPowers)
                if(('delta' in dict) and ('PoorSignalLevel' in dict) and ('Meditation' in dict) and ('Attention' in dict)):
                    if(not self.med_value == dict.get('Meditation') or not self.at_value == dict.get('Attention') or not self.signal == dict.get('PoorSignalLevel')):
                        print(dict)
                        self.med_value = int(dict.get('Meditation'))
                        self.at_value = int(dict.get('Attention'))
                        self.signal = int(dict.get('PoorSignalLevel'))
                        self.EEG_queue.put([self.med_value, self.at_value, self.signal])
                        self.EEG_t_last = dt.datetime.now()


                if(self.EEG_running == -1):
                    print("EEG_paused")
                    time.sleep(.5)

    def start_EEG (self):
        if(not self.EEG_status):
            self.print_log('[-] EEG sensor not connected')
        else:
            self.EEG_running = 1
            threading.Thread(target = self.get_EEG, args=()).start()

    def pause_EEG(self):
        self.print_log("[+] Pause EEG")
        self.EEG_running = -1

    def continue_EEG(self):
        self.print_log("[+] Continue EEG")
        self.EEG_running = 1

    def stop_EEG (self):
        self.print_log("[+] Stop EEG")
        self.EEG_running = 0


    def connect_IMU(self):
        self.IMU_status = True
        if(not debug_mock):
            mpu9250 = FaBo9Axis_MPU9250.MPU9250()
            self.print_log("[+]MPU9250 conected")
        else:
            self.print_log("[!]MPU9250 mocking mode")

    def get_IMU(self):
        while(self.IMU_running):
            if(self.IMU_running == 1):
                if(not debug_mock):
                    self.accel = mpu9250.readAccel()
                    self.gyro = mpu9250.readGyro()
                    self.mag = mpu9250.readMagnet()
                else:
                    self.accel = {'x' : randrange(-2, 2), 'y' : randrange(-2, 2), 'z' : randrange(-2, 2)}
                    self.gyro = {'x' : randrange(-180, 180, 5), 'y' : randrange(-180, 180, 5), 'z' : randrange(-180, 180, 5)}
                    self.mag = {'x' : randrange(-180, 180, 5), 'y' : randrange(-180, 180, 5), 'z' : randrange(-180, 180, 5)}
                self.IMU_queue.put([self.accel['x'], self.accel['y'], self.accel['z'], self.gyro['x'], self.gyro['y'], self.gyro['z'], self.mag['x'], self.mag['y'], self.mag['z']])
                time.sleep(0.2)
            elif(self.IMU_running == -1):
                print("IMU_paused")
                time.sleep(.5)

    def start_IMU (self):
        if(not self.IMU_status):
            self.print_log('[-] IMU sensor not connected')
        else:
            self.IMU_running = 1
            threading.Thread(target = self.get_IMU, args=()).start()

    def pause_IMU(self):
        self.print_log("[+] Pause IMU")
        self.IMU_running = -1

    def continue_IMU(self):
        self.print_log("[+] Continue IMU")
        self.IMU_running = 1

    def stop_IMU (self):
        self.print_log("[+] Stop IMU")
        self.IMU_running = 0

    def connect_HEART(self):
        self.HEART_status = True
        if(not debug_mock):
            self.heart_sensor = max30102.MAX30102()
            self.print_log("[+]MAX30102 conected")
        else:
            self.print_log("[!]MPU9250 mocking mode")

    def display_heartrate(beat, bpm, avg_bpm):
        pass

    def start_OSC_sender(self):
        self.client = udp_client.SimpleUDPClient(IP, PORT)
        self.SENDER_running = 1
        while(self.SENDER_running):
            if(self.EEG_enable == 1 and not self.EEG_queue.empty()):
                self.print_log("send_EEG")
                self.client.send_message("/EEG", self.EEG_queue.get())
            if(self.IMU_enable == 1 and not self.IMU_queue.empty()):
                self.print_log("send_IMU")
                print(self.IMU_queue.get())
                self.client.send_message("/IMU", self.IMU_queue.get())

    def stop_OSC_sender(self):
        self.SENDER_running = 0
        pass

    def end_file(self):
        if(logmode):
            self.log_file.close()

try:
    S = SensorMSG()
    S.start_EEG()
    S.connect_IMU()
    S.start_IMU ()
    S.start_OSC_sender()
finally:
    S.stop_EEG()
    S.stop_IMU()
    S.stop_OSC_sender()
    S.end_file()
