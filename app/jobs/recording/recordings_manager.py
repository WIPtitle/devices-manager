from abc import abstractmethod

from app.models.recording import Recording


class RecordingsManager:
    @abstractmethod
    def is_recording(self, camera_ip: str):
        pass

    @abstractmethod
    def start_recording(self, recording: Recording):
        pass

    @abstractmethod
    def stop_recording(self, recording: Recording):
        pass

    @abstractmethod
    def delete_recording(self, recording: Recording):
        pass

    @abstractmethod
    def get_current_recording_by_camera_ip(self, camera_ip: str):
        pass
