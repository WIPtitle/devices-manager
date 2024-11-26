from abc import ABC, abstractmethod
from typing import List, Sequence

from app.models.device_group import DeviceGroup


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
    def find_all_devices_groups(self) -> Sequence[DeviceGroup]:
        pass
