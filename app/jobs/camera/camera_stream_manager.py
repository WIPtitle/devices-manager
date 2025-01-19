from abc import abstractmethod

from app.models.camera import Camera


class CameraStreamManager:
    @abstractmethod
    def start_streaming(self, camera: Camera):
        pass

    @abstractmethod
    def stop_streaming(self, camera: Camera):
        pass