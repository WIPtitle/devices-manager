from abc import abstractmethod


class AlarmManager:
    @abstractmethod
    def on_sensor_triggered(self, sensor_pin: int):
        """Called when a sensor is triggered (goes HIGH)"""
        pass

    @abstractmethod
    def stop_alarm(self):
        pass