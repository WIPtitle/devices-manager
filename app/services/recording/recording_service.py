from abc import ABC, abstractmethod
from typing import Sequence

from app.models.recording import Recording


class RecordingService(ABC):
    @abstractmethod
    def get_by_id(self, rec_id: int) -> Recording:
        pass

    @abstractmethod
    def create_and_start(self, recording: Recording) -> Recording:
        pass

    @abstractmethod
    def stop_by_camera_ip(self, camera_ip: str) -> Recording:
        pass

    @abstractmethod
    def delete_by_id(self, rec_id: int) -> Recording:
        pass

    @abstractmethod
    def get_all(self) -> Sequence[Recording]:
        pass

    @abstractmethod
    def stream(self, request, rec_id: int):
        pass

    @abstractmethod
    def download(self, rec_id: int):
        pass

