#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
import datetime
import pytz
import numpy as np
import cv2
import queue

class AlertEntity:
    def __init__(self, **kwargs):
        self.status = kwargs.get('status', False)
        self.alert_level = 0

    def set_status(self, status):
        self.status = status

    def get_status(self):
        return self.status
    
class VideoAlert(AlertEntity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_frame = None
        self._frame_diff = None
        self._default_threshold = 0.07
        self._threshold = 0.07
        self._init_queue()
        
    def _init_queue(self):
        self._frame_queue = queue.deque(maxlen=300)
        
    def _set_baseline(self):
        self._threshold = self._default_threshold
        self._init_queue()       
        
    def add_frame(self, frame):
        # Konvertiere den Frame in Graustufen
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Wende Gaussian Blur an, um Rauschen zu reduzieren
        blurred_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)
        
        if self._last_frame is not None:
            # Berechne die Differenz zwischen dem aktuellen und dem letzten Frame
            gray_last_frame = cv2.cvtColor(self._last_frame, cv2.COLOR_BGR2GRAY)
            blurred_last_frame = cv2.GaussianBlur(gray_last_frame, (7, 7), 0)
            frame_diff = cv2.absdiff(blurred_last_frame, blurred_frame)

            # Schwellwert anwenden, um nur signifikante Änderungen zu berücksichtigen
            _, thresh = cv2.threshold(frame_diff, 3, 255, cv2.THRESH_BINARY)

            # Zähle die Anzahl der nicht-null Pixel in der Differenzmatrix
            diff_value = cv2.countNonZero(thresh)
    
            # Berechne die Gesamtanzahl der Pixel im Bild
            total_pixels = frame.shape[0] * frame.shape[1]  # Höhe * Breite
    
            # Berechne den Anteil der Pixel mit Differenz
            diff_ratio = diff_value / total_pixels if total_pixels > 0 else 0

            # Speichere das Ergebnis mit Zeitstempel in der Queue
            timestamp = datetime.datetime.now(pytz.timezone('Europe/Berlin')).isoformat()
            self._frame_queue.append((timestamp, diff_ratio))

        # Speichere den aktuellen Frame als letzten Frame
        self._last_frame = frame
        
        self._evaluate()

    def _evaluate(self):
        try:
            video_data = self.get_frame_diffs()
            now = datetime.datetime.fromisoformat(video_data[-1][0])
            levels = [data[1] for data in video_data if now - datetime.datetime.fromisoformat(data[0]) <= datetime.timedelta(seconds=30)]
            self.alert_level = float(np.mean(levels))
            self.status = self.alert_level > self._threshold
        except:
            pass

    def get_frame_diffs(self):
        return list(self._frame_queue)

    
class AudioAlert(AlertEntity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._data = None
        self._threshold = kwargs.get('threshold', 0.4)
    
    def evaluate(self, data):
        self._set_data(data)
        self._evaluate()
        
    def _set_data(self, data):
        self.data = data
        
    def _evaluate(self):
        try:
            if len(self.data)<=10:
                return
            
            now = datetime.datetime.fromisoformat(self.data[-1]['time'])
            # Filtere die Daten der letzten 30 Sekunden
            recent_data = [data for data in self.data if now - datetime.datetime.fromisoformat(data['time']) <= datetime.timedelta(seconds=30)]
            
            if not recent_data:
                self.alert_level = 0
                self.status = False
                return
            
            # Extrahiere die Zeit- und Levelwerte
            times = np.array([datetime.datetime.fromisoformat(data['time']).timestamp() for data in recent_data])
            levels = np.array([data.get('level', 0) for data in recent_data])
            
            # Berechne die Flächen
            area_above = np.trapz(levels[levels > 0], times[levels > 0])
            area_below = np.trapz(levels[levels < 0], times[levels < 0])
            
            # Bestimme den Anteil
            total_area = abs(area_above) + abs(area_below)
            self.alert_level = area_above / total_area if total_area > 0 else 0
            self.status = self.alert_level > self._threshold
        except Exception as e:
            print(f"Error during evaluation: {e}")

    def _evaluate_lin(self):
        try:
            now = datetime.datetime.fromisoformat(self.data[-1]['time'])
            levels = [data.get('level') for data in self.data if now - datetime.datetime.fromisoformat(data['time']) <= datetime.timedelta(seconds=30)]
            self.alert_level = float(np.sum(np.array(levels) > 0) / len(levels) if len(levels) > 0 else 0)
            self.status = self.alert_level > self._threshold
        except:
            pass


class AlertFrame:
    def __init__(self, **kwargs):
        self.enabled = kwargs.get('enabled', True)
        self.alert_entities = []
        
    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def toggle(self):
        self.enabled = not self.enabled

    def add_alert_entity(self, alert_entity):
        if isinstance(alert_entity, AlertEntity):
            self.alert_entities.append(alert_entity)
        else:
            raise ValueError("Only AlertEntity instances can be added.")

    def status(self):
        if self.enabled==False:
            return self.enabled
        return any(entity.get_status() for entity in self.alert_entities)


    def level(self):
        return max((entity.alert_level for entity in self.alert_entities), default=0)



if __name__ == "__main__":
    self = VideoAlert()

    # Beispiel für das Hinzufügen von Frames (hier simuliert)
    cap = cv2.VideoCapture(1)  # Verwende die Standardkamera

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        self.add_frame(frame)

        # Zeige den aktuellen Frame an
        cv2.imshow("Video Stream", frame)
        
        try:
            print(list(self._frame_queue)[-1])
            print(self.alert_level)
            print(self.status)
        except:
            pass

        # Beenden, wenn 'q' gedrückt wird
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
