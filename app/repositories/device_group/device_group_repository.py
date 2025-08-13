from abc import ABC, abstractmethod
from typing import Sequence
from app.models.device_group import DeviceGroup
from app.models.sensor import Sensor


class DeviceGroupRepository(ABC):
    @abstractmethod
    def create_device_group(self, device_group: DeviceGroup) -> DeviceGroup:
        pass

    @abstractmethod
    def delete_device_group(self, group_id: int):
        pass

    @abstractmethod
    def update_device_group(self, group: DeviceGroup) -> DeviceGroup:
        pass

    @abstractmethod
    def find_device_group_by_id(self, device_group_id: int) -> DeviceGroup:
        pass

    @abstractmethod
    def find_device_group_sensors_by_id(self, device_group_id: int) -> Sequence[Sensor]:
        pass

    @abstractmethod
    def update_device_group_sensors_by_id(self, device_group_id: int, sensor_pins: Sequence[int]) -> Sequence[Sensor]:
        pass

    @abstractmethod
    def find_all_devices_groups(self) -> Sequence[DeviceGroup]:
        pass

    @abstractmethod
    def find_listening_device_group(self) -> DeviceGroup:
        pass

    @abstractmethod
    def are_all_groups_idle(self) -> bool:
        pass