from typing import Sequence

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.models.camera import Camera
from app.repositories.camera.camera_repository import CameraRepository
from app.services.camera.camera_service import CameraService


class CameraServiceImpl(CameraService):
    def __init__(self, camera_repository: CameraRepository):
        self.camera_repository = camera_repository
        self.camera_threads = {}
        self.current_frames = {}


    def get_by_ip(self, ip: str) -> Camera:
        return self.camera_repository.find_by_ip(ip)


    def create(self, camera: Camera) -> Camera:
        # Stop user from adding an unreachable camera.
        # A camera can still become unreachable but prevent creating one that already is.
        if not camera.is_reachable():
            raise BadRequestException("Camera is not reachable")

        camera = self.camera_repository.create(camera)
        return camera


    def update(self, ip: str, camera: Camera) -> Camera:
        if camera.ip != ip:
            raise UnupdateableDataException("Can't update ip")

        # Stop user from updating to an unreachable camera.
        # A camera can still become unreachable but prevent creating one that already is.
        if not camera.is_reachable():
            raise BadRequestException("Camera is not reachable")

        camera = self.camera_repository.update(camera)
        return camera


    def delete_by_ip(self, ip: str) -> Camera:
        camera = self.camera_repository.delete_by_ip(ip)
        return camera


    def get_all(self) -> Sequence[Camera]:
        return self.camera_repository.find_all()


    def get_current_frame(self, ip: str):
        return None