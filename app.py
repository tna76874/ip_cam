#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, Response, stream_with_context, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import time
from streams import *
from alerts import *
import base64
import pytz
import wave


class GenerateFrames:
    def __init__(self, socketio=None, cam=None):
        self.cam = cam
        self.socketio = socketio
        self.clients = dict()
        self.running = Event()
        self.thread = None
        self.alert = False
        
        self._alert_a = AudioAlert(threshold=0.6)
        self._alert_v = VideoAlert()
        self._alert = AlertFrame()
        self._alert.add_alert_entity(self._alert_a)
        self._alert.add_alert_entity(self._alert_v)

    def start(self):
        if not self.running.is_set():
            self.running.set()
            self.thread = Thread(target=self._generate_frames)
            self.thread.start()

    def stop(self):
        self.running.clear()
        if self.thread is not None:
            self.thread.join()
    
    def _compress_frame(self, frame=None, quality=100):
        if quality!=100:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
        else:
            buffer = frame
        encoded = base64.b64encode(buffer).decode('utf-8')
        return encoded

    def _generate_frames(self):
        quality_mapping = {
            0.1: 100,
            1: 80,
            2: 30,
            5: 10,
        }
        while self.running.is_set():
            self.cam.a.start_monitoring()
            
            frame = self.cam.get_frame() 
            if frame is not None:
                self._alert_v.add_frame(frame)
                video_json =  {
                                'time' : datetime.datetime.now(pytz.timezone('Europe/Berlin')).isoformat(),
                              }
                for client in self.clients.keys():
                    timediff = self.clients.get(client, 0) or 0
                    quality = None
                    for threshold, q in quality_mapping.items():
                        if timediff <= threshold:
                            quality = q
                            break
                        
                    if quality is not None:
                        video_json['data'] = self._compress_frame(frame=frame, quality=quality)
                    else:
                        video_json['data'] = False
                        
                    socketio.emit('frame', video_json, room=client)
                        
            
            audio_data = self.cam.get_audio_data()
            if audio_data!=[]:
                self._alert_a.evaluate(audio_data) 
                alert_json = {'audio' : self._alert_a.alert_level}
            else:
                alert_json = {'audio' : 0 }
                
            alert_json.update({
                'alert' : self._alert.status(),
                'video' : self._alert_v.alert_level,
            })

            socketio.emit('alert', alert_json)       
            
    def add_client(self, sid):
        self.clients[request.sid] = 0
        
    def update_client_timediff(self, client=None, diff=None):
        if client==None:
            return
        self.clients[client] = diff

    def remove_client(self, sid):
        if sid in self.clients.keys():
            self.clients.pop(sid)
        if not self.clients:
            self.stop()


conf = ConfigReader('data/config.yml')
cam = CameraEntity(hostname=conf.get_hostname(),
                   subnet=conf.get_subnet(),
                   mac=conf.get_mac(),
                   baseline=conf.get_baseline(),
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
        
    frame_generator.cam.record_audio_baseline()
    frame_generator._alert_v._set_baseline()
        
    response = {
        'status': 'success',
        'message': 'Baseline gesetzt',
    }
    return jsonify(response)

@app.route('/api/alert_enable', methods=['GET'])
def api_alert_enable():
    frame_generator._alert.enable()
    return jsonify({'status': frame_generator._alert.enabled})

@app.route('/api/alert_disable', methods=['GET'])
def api_alert_disable():
    frame_generator._alert.disable()
    return jsonify({'status': frame_generator._alert.enabled})

@app.route('/api/alert_toggle', methods=['GET'])
def api_alert_toggle():
    frame_generator._alert.toggle()
    return jsonify({'status': frame_generator._alert.enabled})

@app.route('/api/alert_is_enabled', methods=['GET'])
def api_alert_is_enabled():
    return jsonify({'status': frame_generator._alert.enabled})

@app.route('/api/server_time', methods=['GET'])
def get_server_time():
    server_time = datetime.datetime.now(pytz.timezone('Europe/Berlin')).isoformat()
    return jsonify({'time': server_time})

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
    
@socketio.on('time_diff')
def handle_time_diff(time_diff):
    frame_generator.update_client_timediff(client=request.sid, diff=time_diff)

if __name__ == '__main__':
    pass
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)