from abc import ABC, abstractmethod
from typing import Sequence

from app.models.recording import Recording


class RecordingService(ABC):
    @abstractmethod
    def get_by_id(self, rec_id: int) -> Recording:
        pass

    @abstractmethod
    def create(self, recording: Recording) -> Recording:
        pass

    @abstractmethod
    def stop(self, rec_id: int) -> Recording:
        pass

    @abstractmethod
    def delete_by_id(self, rec_id: int) -> Recording:
        pass

    @abstractmethod
    def get_all(self) -> Sequence[Recording]:
        pass

    @abstractmethod
    def stream(self, rec_id: int):
        pass

    @abstractmethod
    def download(self, rec_id: int):
        pass
