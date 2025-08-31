from abc import ABC, abstractmethod
from typing import Sequence, List
from app.models.sensor import Sensor


class SensorService(ABC):
    @abstractmethod
    def get_by_id(self, sensor_id: str) -> Sensor:
        pass

    @abstractmethod
    def create(self, sensor: Sensor) -> Sensor:
        pass

    @abstractmethod
    def update(self, sensor_id: str, sensor: Sensor) -> Sensor:
        pass

    @abstractmethod
    def delete_by_id(self, sensor_id: str) -> Sensor:
        pass

    @abstractmethod
    def get_all(self) -> Sequence[Sensor]:
        pass

    @abstractmethod
    def get_status_by_id(self, sensor_id: str) -> int:
        """Get sensor status: 0=LOW, 1=HIGH"""
        pass

    @abstractmethod
    async def get_sensor_status_stream_by_id(self, sensor_id: str):
        """Stream sensor status updates"""
        pass

    @abstractmethod
    def get_available_gpio_servers(self) -> List[str]:
        """Get list of available GPIO monitor servers"""
        pass