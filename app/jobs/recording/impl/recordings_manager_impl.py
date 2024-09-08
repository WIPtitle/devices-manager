from app.jobs.recording.recordings_manager import RecordingsManager

from app.models.recording import Recording
from app.repositories.camera.camera_repository import CameraRepository


class RecordingsManagerImpl(RecordingsManager):
    def __init__(self, camera_repository: CameraRepository):
        self.camera_repository = camera_repository

    def start_recording(self, recording: Recording):
        print("start recording")
        pass

    def stop_recording(self, recording: Recording):
        print("stop recording")
        pass

    def delete_recording(self, recording: Recording):
        print("delete recording")
        pass