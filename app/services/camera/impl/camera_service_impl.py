from typing import Sequence

from app.exceptions.bad_request_exception import BadRequestException
from app.models.camera import Camera
from app.models.recording import RecordingInputDto, Recording
from app.repositories.camera.camera_repository import CameraRepository
from app.services.camera.camera_service import CameraService
from app.services.recording.recording_service import RecordingService


class CameraServiceImpl(CameraService):
    def __init__(self, camera_repository: CameraRepository, recording_service: RecordingService):
        self.camera_repository = camera_repository
        self.recording_service = recording_service

        # Start recording existing cameras on boot
        for camera in self.camera_repository.find_all():
            self.recording_service.create_and_start(Recording.from_dto(RecordingInputDto(camera_ip=camera.ip)))


    def get_by_ip(self, ip: str) -> Camera:
        return self.camera_repository.find_by_ip(ip)


    def create(self, camera: Camera) -> Camera:
        # Stop user from adding an unreachable camera.
        # A camera can still become unreachable but prevent creating one that already is.
        if not camera.is_reachable():
            raise BadRequestException("Camera is not reachable")

        camera = self.camera_repository.create(camera)

        # Start recording new camera
        self.recording_service.create_and_start(Recording.from_dto(RecordingInputDto(camera_ip=camera.ip)))
        return camera


    def delete_by_ip(self, ip: str) -> Camera:
        camera = self.camera_repository.delete_by_ip(ip)
        self.recording_service.stop_by_camera_ip(ip)
        return camera


    def get_all(self) -> Sequence[Camera]:
        return self.camera_repository.find_all()
