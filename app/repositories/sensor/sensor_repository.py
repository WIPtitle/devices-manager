from abc import ABC, abstractmethod
from typing import Sequence
from app.models.sensor import Sensor


class SensorRepository(ABC):
    @abstractmethod
    def find_by_id(self, sensor_id: str) -> Sensor:
        pass

    @abstractmethod
    def find_by_server_and_pin(self, server_url: str, gpio_pin_number: int) -> Sensor:
        pass

    @abstractmethod
    def create(self, sensor: Sensor) -> Sensor:
        pass

    @abstractmethod
    def update(self, sensor: Sensor) -> Sensor:
        pass

    @abstractmethod
    def delete_by_id(self, sensor_id: str) -> Sensor:
        pass

    @abstractmethod
    def find_all(self) -> Sequence[Sensor]:
        pass

    @abstractmethod
    def update_listening(self, sensor: Sensor, listening: bool) -> Sensor:
        pass

    @abstractmethod
    def exists_by_server_and_pin(self, server_url: str, gpio_pin_number: int) -> bool:
        pass