from typing import Sequence

from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.exceptions.validation_exception import ValidationException
from app.jobs.cameras_listener import CamerasListener
from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus
from app.repositories.camera.camera_repository import CameraRepository
from app.services.camera.camera_service_impl import CameraService


class CameraServiceImpl(CameraService):
    def __init__(self, camera_repository: CameraRepository, cameras_listener: CamerasListener):
        self.camera_repository = camera_repository
        self.cameras_listener = cameras_listener

        # When service is created on app init, start listening to already saved cameras.
        for camera in self.camera_repository.find_all():
            self.cameras_listener.add_camera(camera)


    def get_by_ip(self, ip: str) -> Camera:
        return self.camera_repository.find_by_ip(ip)


    def create(self, camera: Camera) -> Camera:
        # Stop user from adding an unreachable camera.
        # A camera can still become unreachable but prevent creating one that already is.
        if not camera.is_reachable():
            raise ValidationException("Camera is not reachable")

        camera = self.camera_repository.create(camera)
        self.cameras_listener.add_camera(camera)
        return camera


    def update(self, ip: str, camera: Camera) -> Camera:
        if camera.ip is not ip:
            raise UnupdateableDataException("Can't update ip")

        camera = self.camera_repository.update(camera)
        self.cameras_listener.update_camera(camera)
        return camera


    def delete_by_ip(self, ip: str) -> Camera:
        camera = self.camera_repository.delete_by_ip(ip)
        self.cameras_listener.remove_camera(camera)
        return camera


    def get_all(self) -> Sequence[Camera]:
        return self.camera_repository.find_all()


    def get_status_by_ip(self, ip: str) -> CameraStatus:
        camera = self.camera_repository.find_by_ip(ip)
        return self.cameras_listener.get_status_by_camera(camera)
