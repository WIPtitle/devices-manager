from abc import ABC, abstractmethod
from typing import Sequence
from app.models.device_group import DeviceGroup
from app.models.sensor import Sensor


class DeviceGroupService(ABC):
    @abstractmethod
    def create_device_group(self, device_group: DeviceGroup) -> DeviceGroup:
        pass

    @abstractmethod
    def delete_device_group(self, group_id: int):
        pass

    @abstractmethod
    def update_device_group(self, group_id: int, group: DeviceGroup) -> DeviceGroup:
        pass

    @abstractmethod
    def get_device_group_by_id(self, group_id: int) -> DeviceGroup:
        pass

    @abstractmethod
    async def get_device_group_status_stream_by_id(self, group_id: int):
        pass

    @abstractmethod
    def get_device_group_sensors_by_id(self, group_id: int) -> Sequence[Sensor]:
        pass

    @abstractmethod
    def update_device_group_sensors_by_id(self, group_id: int, sensor_pins: Sequence[int]) -> Sequence[Sensor]:
        pass

    @abstractmethod
    def get_all_device_groups(self) -> Sequence[DeviceGroup]:
        pass

    @abstractmethod
    def start_listening(self, group_id: int) -> DeviceGroup:
        pass

    @abstractmethod
    def stop_listening(self, group_id: int) -> DeviceGroup:
        pass