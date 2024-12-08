from abc import ABC, abstractmethod
from typing import List

from app.models.device_group import DeviceGroup, Device


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
    '''
    @abstractmethod
    def start_listening(self, group_id: int, force_listening: bool) -> DeviceGroup:
        pass

    @abstractmethod
    def stop_listening(self, group_id: int) -> DeviceGroup:
        pass
    '''