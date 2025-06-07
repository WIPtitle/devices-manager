from abc import ABC, abstractmethod
from typing import Sequence

from app.models.enums.recording_type import RecordingType
from app.models.recording import Recording


class RecordingRepository(ABC):
    @abstractmethod
    def find_by_id(self, rec_id: int) -> Recording:
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Recording:
        pass

    @abstractmethod
    def create(self, recording: Recording) -> Recording:
        pass

    @abstractmethod
    def set_stopped(self, recording: Recording) -> Recording:
        pass

    @abstractmethod
    def delete_by_id(self, rec_id: int) -> Recording:
        pass

    @abstractmethod
    def find_all(self) -> Sequence[Recording]:
        pass

    @abstractmethod
    def find_all_paginated(self, offset: int, recording_type: RecordingType) -> Sequence[Recording]:
        pass
