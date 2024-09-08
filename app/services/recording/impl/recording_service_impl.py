from typing import Sequence

from app.exceptions.validation_exception import ValidationException
from app.jobs.recording.recordings_manager import RecordingsManager
from app.models.recording import Recording
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.recording.recording_repository import RecordingRepository
from app.services.recording.recording_service import RecordingService


class RecordingServiceImpl(RecordingService):
    def __init__(self, recording_repository: RecordingRepository, camera_repository: CameraRepository, recording_manager: RecordingsManager):
        self.recording_repository = recording_repository
        self.camera_repository = camera_repository
        self.recording_manager = recording_manager


    def get_by_id(self, rec_id: int) -> Recording:
        return self.recording_repository.find_by_id(rec_id)


    def create(self, recording: Recording) -> Recording:
        camera = self.camera_repository.find_by_ip(recording.camera_ip) # will throw if not found
        if not camera.is_reachable():
            raise ValidationException("Camera is not reachable")

        recording = self.recording_repository.create(recording)
        self.recording_manager.start_recording(recording)
        return recording


    def stop(self, rec_id: int) -> Recording:
        recording = self.recording_repository.find_by_id(rec_id)
        self.recording_manager.stop_recording(recording)
        return recording


    def delete_by_id(self, rec_id: int) -> Recording:
        recording = self.recording_repository.delete_by_id(rec_id)
        self.recording_manager.delete_recording(recording)
        return recording


    def get_all(self) -> Sequence[Recording]:
        return self.recording_repository.find_all()