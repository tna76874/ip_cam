#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, Response, stream_with_context, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import time
from streams import *
import base64
import pytz
import wave


class GenerateFrames:
    def __init__(self, socketio=None, cam=None):
        self.cam = cam
        self.socketio = socketio
        self.clients = set()
        self.running = Event()
        self.thread = None
        self.alert = False

    def start(self):
        if not self.running.is_set():
            self.running.set()
            self.thread = Thread(target=self._generate_frames)
            self.thread.start()

    def stop(self):
        self.running.clear()
        if self.thread is not None:
            self.thread.join()

    def _generate_frames(self):
        while self.running.is_set():
            self.cam.a.start_monitoring()
            
            frame = self.cam.get_frame() 
            if frame is not None:
                # Konvertiere das Bild in Base64, um es über WebSocket zu senden
                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = base64.b64encode(buffer).decode('utf-8')
                socketio.emit('frame', {'data': frame_data, 'time' : datetime.datetime.now(pytz.timezone('Europe/Berlin')).isoformat()})

            audio_data = self.cam.get_audio_data()
            if audio_data!=[]:

                now = datetime.datetime.fromisoformat(audio_data[-1]['time'])
                
                levels = [data.get('level') for data in audio_data if now - datetime.datetime.fromisoformat(data['time']) <= datetime.timedelta(seconds=30)]
                alert_ratio = float(np.sum(np.array(levels) > 0) / len(levels) if len(levels) > 0 else 0)
                self.alert = alert_ratio >= 0.6

                audio_json = {
                    'alert' : self.alert,
                    'alert_ratio' : alert_ratio,
                    'history': [audio_data[-1]],
                }
                socketio.emit('audio', audio_json)       
            
    def add_client(self, sid):
        self.clients.add(sid)

    def remove_client(self, sid):
        if sid in self.clients:
            self.clients.remove(sid)
        if not self.clients:
            self.stop()


conf = ConfigReader('data/config.yml')
cam = CameraEntity(hostname=conf.get_hostname(),
                   subnet=conf.get_subnet(),
                   mac=conf.get_mac(),
                   username=conf.get_auth().get('user'),
                   password=conf.get_auth().get('pw'))
cam.init_streams()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

frame_generator = GenerateFrames(socketio=socketio, cam=cam)

@app.route('/api/set_baseline', methods=['POST'])
def set_baseline():
    data = request.get_json()

    while frame_generator.cam.a.current_level==None:
        frame_generator.cam._init_audio_stream()
        frame_generator.cam.a.start_monitoring()
        
    frame_generator.cam.a._record_baseline()
    response = {
        'status': 'success',
        'message': 'Baseline gesetzt',
    }
    return jsonify(response)

@app.route('/alert.mp3')
def serve_mp3():
    return send_from_directory('static', 'alert.mp3')

@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    frame_generator.add_client(request.sid)
    if not frame_generator.running.is_set():
        frame_generator.start()

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    frame_generator.remove_client(request.sid)

if __name__ == '__main__':
    pass
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)