from abc import abstractmethod

from app.models.enums.camera_status import CameraStatus
from app.models.enums.reed_status import ReedStatus


class AlarmManager:
    @abstractmethod
    def on_camera_changed_status(self, camera_ip: str, name: str, status: CameraStatus, blob: bytes | None):
        pass

    @abstractmethod
    def on_reed_changed_status(self, name: str, status: ReedStatus):
        pass

    @abstractmethod
    def on_all_devices_stopped_listening(self):
        pass