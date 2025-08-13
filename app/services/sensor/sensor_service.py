from abc import ABC, abstractmethod
from typing import Sequence
from app.models.sensor import Sensor


class SensorService(ABC):
    @abstractmethod
    def get_by_pin(self, gpio_pin_number: int) -> Sensor:
        pass

    @abstractmethod
    def create(self, sensor: Sensor) -> Sensor:
        pass

    @abstractmethod
    def update(self, gpio_pin_number: int, sensor: Sensor) -> Sensor:
        pass

    @abstractmethod
    def delete_by_pin(self, gpio_pin_number: int) -> Sensor:
        pass

    @abstractmethod
    def get_all(self) -> Sequence[Sensor]:
        pass

    @abstractmethod
    def get_status_by_pin(self, gpio_pin_number: int) -> int:
        """Get sensor status: 0=LOW, 1=HIGH"""
        pass