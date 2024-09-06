from abc import abstractmethod

from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


class CamerasListener:
    @abstractmethod
    def add_camera(self, camera: Camera):
        pass

    @abstractmethod
    def update_camera(self, camera: Camera):
        pass

    @abstractmethod
    def remove_camera(self, camera: Camera):
        pass

    @abstractmethod
    def get_status_by_camera(self, camera: Camera) -> CameraStatus:
        pass
