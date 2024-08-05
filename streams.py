#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
import requests
from requests.auth import HTTPBasicAuth
import numpy as np
import cv2
import yaml
import datetime
import threading
import queue
import time
import pytz
import nmap

from network import *

class ConfigReader:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config_data = self.load_config()

    def load_config(self):
        with open(self.config_file, 'r') as file:
            return yaml.safe_load(file)
    
    def get_ip(self):
        return self.config_data.get('ip', None)
    
    def get_hostname(self):
        return self.config_data.get('host', {}).get('name')
    
    def get_subnet(self):
        return self.config_data.get('host', {}).get('subnet')

    def get_mac(self):
        return self.config_data.get('host', {}).get('mac')
    
    def get_baseline(self):
        return self.config_data.get('baseline')

    def get_auth(self):
        return {
            'user': self.config_data.get('auth', {}).get('user'),
            'pw': self.config_data.get('auth', {}).get('pw')
        }

class CameraEntity:
    def __init__(self, **kwargs):
        self.hostname = kwargs.get('hostname')
        self._nd = NetworkDevice(hostname=self.hostname, subnet = kwargs.get('subnet'), mac=kwargs.get('mac'))
        self._get_ip()
        
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.video_url = f'http://{self.ip}/video.cgi'
        self.video_url_auth = f'http://{self.username}:{self.password}@{self.ip}:80/video.cgi'
        self.audio_url = f'http://{self.ip}/audio.cgi'
        
        self.baseline = kwargs.get('baseline')
        
        self.v = None
        self.a = None
        
    def _get_ip(self):
        self.ip = self._nd.get_ip()
    
    def init_streams(self):
        self._init_audio_stream()
        self._init_video_stream()
        
    def _init_video_stream(self):
        self.v = VideoMonitor(self.get_video_stream())
    
    def _init_audio_stream(self):
        self.a = AudioMonitor(self.get_audio_stream(), baseline=self.baseline)
        
    def get_frame(self):
        frame=None
        if isinstance(self.v,VideoMonitor):
            frame = self.v.get_frame()
        while isinstance(frame,type(None)):
            self._get_ip()
            self._init_video_stream()
            frame = self.v.get_frame()
        return frame
            
    def get_audio_data(self):
        audio = [{'level': None}]
        if not isinstance(self.a,AudioMonitor):
            self._init_audio_stream()
            
        self.a.start_monitoring()
        audio = self.a.get_recent_audio_data()

        passed = False
        while not passed:
            while len(audio)==0:
                time.sleep(0.1)
                audio = self.a.get_recent_audio_data()
            
            passed = audio[-1].get('level') != None
            if not passed:
                self._get_ip()
                self._init_audio_stream()
                self.a.start_monitoring()
                
        return audio

    def get_video_stream(self):
        return cv2.VideoCapture(self.video_url_auth)

    def get_audio_stream(self):
        try:
            resp = requests.get(self.audio_url, stream=True, verify=False, timeout=5, auth=HTTPBasicAuth(self.username, self.password))
            if resp.status_code != 200:
                return None
            return resp
        except Exception as e:
            print(f"Error retrieving audio stream: {e}")
            return None
            
class VideoMonitor:
    def __init__(self, cap):
        self.capture = cap
        if not self.capture.isOpened():
            raise ValueError("Konnte den VideoStream nicht öffnen.")

    def get_frame(self):
        try:
            ret, frame = self.capture.read()
            if ret==False:
                return None
            return frame
        except:
            return None

    def stop(self):
        self.capture.release()


class AudioMonitor:
    def __init__(self, audio_stream, **kwargs):
        self.audio_stream = audio_stream
        self.threshold = kwargs.get('threshold', 1.5)  # Schwellenwert für den Alarm in dB
        self.duration = kwargs.get('duration', 6)      # Dauer der Baseline-Aufnahme
        self.sample_rate = kwargs.get('sample_rate', 8000)  # Abtastrate, Standardwert 8000
        self.baseline = kwargs.get('baseline', 21)
        self.chunk = 1024  # Größe der Datenblöcke, die verarbeitet werden
        self.history_duration = 10 * 60  # 10 Minuten in Sekunden
        self.history_chunk_count = int(self.history_duration * self.sample_rate / self.chunk)
        self._init_queue()
        self.running = False
        self.alertlevel = None
        self.current_level = None
        
    def _init_queue(self):
        self.audio_data_queue = queue.deque(maxlen=self.history_chunk_count)

    def get_chunk(self):
        if self.audio_stream==None:
            return None
        return self.audio_stream.raw.read(self.chunk)

    def _calculate_db(self, audio_data):
        try:
            # Überprüfe, ob audio_data leer ist
            if len(audio_data) == 0:
                return None
    
            # Berechne den RMS-Wert
            mean_square = np.mean(np.square(audio_data))
    
            # Überprüfe auf negative Werte oder NaNs
            if np.isnan(mean_square) or mean_square < 0:
                raise None
    
            rms = np.sqrt(mean_square)
    
            # Verhindere log10 von 0, indem du den RMS-Wert auf einen minimalen Wert setzt
            if rms == 0:
                return None
    
            db = 20 * np.log10(rms)
            return db
        except:
            return None

    def _record_baseline(self):
        print("Recording baseline...")
        num_chunks = int(self.duration * self.sample_rate / self.chunk)
        audio_data = []

        for _ in range(num_chunks):
            data = self.get_chunk()
            if isinstance(data, type(None)):
                return
            audio_data.append(np.frombuffer(data, dtype=np.int16))

        audio_data = np.concatenate(audio_data)
        self.baseline = self._calculate_db(audio_data)
        self._init_queue()
        print(f"Baseline recorded: {self.baseline}")

    def _monitor_audio(self):
        while self.running:
            data = self.get_chunk()
            if not data:
                break
            audio_data = np.frombuffer(data, dtype=np.int16)
            self.current_level = self._calculate_db(audio_data)
            if self.current_level is None:
                continue

            self.alertlevel = self.baseline + self.threshold
            self.audio_data_queue.append({'level' : float(self.current_level)-float(self.alertlevel), 'time' : datetime.datetime.now(pytz.timezone('Europe/Berlin')).isoformat()})
            # if current_level > self.alertlevel:
            #     print(f"{datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')} {self.alertlevel} / {current_level}: ALERT")
            # else:
            #     print(f"{datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')} {self.alertlevel} / {current_level}")

            # print(float(current_level)-float(self.alertlevel))
            
    def start_monitoring(self):
        if self.running == False:
            if self.baseline==None:
                self._record_baseline()
            print("Starting audio monitoring...")
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_audio)
            self.monitor_thread.start()

    def stop_monitoring(self):
        print("Stopping audio monitoring...")
        self.running = False
        self.monitor_thread.join()
        print("Audio monitoring stopped.")

    def get_recent_audio_data(self):
        return list(self.audio_data_queue)



# Beispiel zur Verwendung der Klasse
if __name__ == "__main__":
    conf = ConfigReader('data/config.yml')
    self = CameraEntity(ip=conf.get_ip(),
                        username=conf.get_auth().get('user'),
                        password=conf.get_auth().get('pw'))
    self.init_streams()
    self.a.start_monitoring()
    #self.a.stop_monitoring()
    # mon = AudioMonitor(self.get_audio_stream())
    # mon.monitor_audio()


