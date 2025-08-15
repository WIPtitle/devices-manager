from abc import abstractmethod
from app.models.sensor import Sensor


class SensorsListener:
    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def add_sensor(self, sensor: Sensor):
        pass

    @abstractmethod
    def update_sensor(self, sensor: Sensor):
        pass

    @abstractmethod
    def remove_sensor(self, sensor: Sensor):
        pass

    @abstractmethod
    def get_status_by_sensor(self, sensor: Sensor) -> int:
        """Returns 0 for LOW, 1 for HIGH"""
        pass