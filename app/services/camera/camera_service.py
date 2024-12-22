from abc import ABC, abstractmethod
from typing import Sequence

from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


class CameraService(ABC):
    @abstractmethod
    def get_by_ip(self, ip: str) -> Camera:
        pass

    @abstractmethod
    def create(self, camera: Camera) -> Camera:
        pass

    @abstractmethod
    def update(self, ip: str, camera: Camera) -> Camera:
        pass

    @abstractmethod
    def delete_by_ip(self, ip: str) -> Camera:
        pass

    @abstractmethod
    def get_all(self) -> Sequence[Camera]:
        pass

    @abstractmethod
    def get_status_by_ip(self, ip: str) -> CameraStatus:
        pass

    @abstractmethod
    def get_current_frame(self, ip: str):
        pass
