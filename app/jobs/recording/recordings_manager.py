from abc import abstractmethod

from app.models.recording import Recording


class RecordingsManager:
    @abstractmethod
    def start_recording(self, recording: Recording):
        pass

    @abstractmethod
    def stop_recording(self, recording: Recording):
        pass

    @abstractmethod
    def delete_recording(self, recording: Recording):
        pass