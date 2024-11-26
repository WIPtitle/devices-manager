from abc import ABC, abstractmethod
from typing import Sequence

from app.models.camera import Camera
from app.models.reed import Reed
from app.models.device_group import DeviceGroup


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
    def get_device_group_cameras_by_id(self, group_id: int) -> Sequence[Camera]:
        pass

    @abstractmethod
    def get_device_group_reeds_by_id(self, group_id: int) -> Sequence[Reed]:
        pass

    @abstractmethod
    def update_device_group_cameras_by_id(self, group_id: int, camera_ips: Sequence[str]) -> Sequence[Camera]:
        pass

    @abstractmethod
    def update_device_group_reeds_by_id(self, group_id: int, reed_pins: Sequence[int]) -> Sequence[Reed]:
        pass

    @abstractmethod
    def get_all_device_groups(self) -> Sequence[DeviceGroup]:
        pass
    '''
    @abstractmethod
    def start_listening(self, group_id: int, force_listening: bool) -> DeviceGroup:
        pass

    @abstractmethod
    def stop_listening(self, group_id: int) -> DeviceGroup:
        pass
    '''