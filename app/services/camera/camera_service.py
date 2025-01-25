from abc import ABC, abstractmethod
from typing import Sequence

from app.models.camera import Camera


class CameraService(ABC):
    @abstractmethod
    def get_by_ip(self, ip: str) -> Camera:
        pass

    @abstractmethod
    def create(self, camera: Camera) -> Camera:
        pass

    @abstractmethod
    def delete_by_ip(self, ip: str) -> Camera:
        pass

    @abstractmethod
    def get_all(self) -> Sequence[Camera]:
        pass
