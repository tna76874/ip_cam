#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
import datetime
import pytz
import numpy as np

class AlertEntity:
    def __init__(self, **kwargs):
        self.status = kwargs.get('status', False)
        self.alert_level = 0

    def set_status(self, status):
        self.status = status

    def get_status(self):
        return self.status
    
class AudioAlert(AlertEntity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._data = None
        self._threshold = kwargs.get('threshold', 0.6)
    
    def evaluate(self, data):
        self._set_data(data)
        self._evaluate()
        
    def _set_data(self, data):
        self.data = data
        
    def _evaluate_integral(self):
        try:
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

    def _evaluate(self):
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



# Beispielverwendung
if __name__ == "__main__":
    pass