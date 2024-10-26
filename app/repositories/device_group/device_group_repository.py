from abc import ABC, abstractmethod
from typing import List

from app.models.device_group import Device, DeviceGroup


class DeviceGroupRepository(ABC):
    @abstractmethod
    def create_device(self, device: Device) -> Device:
        pass

    @abstractmethod
    def delete_device(self, device_id: int):
        pass

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
    def update_devices_in_group(self, group_id: int, devices: List[Device]) -> List[Device]:
        pass

    @abstractmethod
    def find_device_by_id(self, device_id: int) -> Device:
        pass

    @abstractmethod
    def find_device_group_by_group_id(self, device_group_id: int) -> DeviceGroup:
        pass

    @abstractmethod
    def find_device_list_by_id(self, group_id: int) -> List[Device]:
        pass

    @abstractmethod
    def find_device_group_list_by_device_id(self, device_id: int) -> List[DeviceGroup]:
        pass
