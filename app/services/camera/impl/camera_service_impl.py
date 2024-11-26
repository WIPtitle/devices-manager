import threading
from typing import Sequence

import cv2

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.jobs.camera.cameras_listener import CamerasListener
from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus
from app.repositories.camera.camera_repository import CameraRepository
from app.services.camera.camera_service import CameraService


class CameraServiceImpl(CameraService):
    def __init__(self, camera_repository: CameraRepository, cameras_listener: CamerasListener):
        self.camera_repository = camera_repository
        self.cameras_listener = cameras_listener
        self.camera_threads = {}
        self.current_frames = {}

        # When service is created on app init, start listening to already saved cameras.
        # Also start streaming process
        for camera in self.camera_repository.find_all():
            self.cameras_listener.add_camera(camera)
            # Start streaming process
            try:
                thread = threading.Thread(target=self.get_frames, args=(camera.ip,), daemon=True)
                self.camera_threads[camera.ip] = thread
                thread.start()
            except Exception as e:
                print("Error starting thread for camera", camera.ip, e)


    def get_by_ip(self, ip: str) -> Camera:
        return self.camera_repository.find_by_ip(ip)


    def create(self, camera: Camera) -> Camera:
        # Stop user from adding an unreachable camera.
        # A camera can still become unreachable but prevent creating one that already is.
        if not camera.is_reachable():
            raise BadRequestException("Camera is not reachable")

        camera = self.camera_repository.create(camera)

        self.cameras_listener.add_camera(camera)
        return camera


    def update(self, ip: str, camera: Camera) -> Camera:
        if camera.ip != ip:
            raise UnupdateableDataException("Can't update ip")

        if camera.listening:
            raise BadRequestException("Can't set listening here")

        if self.camera_repository.find_by_ip(ip).listening:
            raise BadRequestException("Can't update while listening")

        # Stop user from updating to an unreachable camera.
        # A camera can still become unreachable but prevent creating one that already is.
        if not camera.is_reachable():
            raise BadRequestException("Camera is not reachable")

        camera = self.camera_repository.update(camera)
        self.cameras_listener.update_camera(camera)
        return camera


    def delete_by_ip(self, ip: str) -> Camera:
        if self.camera_repository.find_by_ip(ip).listening:
            raise BadRequestException("Can't delete while listening")

        camera = self.camera_repository.delete_by_ip(ip)
        self.cameras_listener.remove_camera(camera)
        return camera


    def get_all(self) -> Sequence[Camera]:
        return self.camera_repository.find_all()


    def get_status_by_ip(self, ip: str) -> CameraStatus:
        camera = self.camera_repository.find_by_ip(ip)
        return self.cameras_listener.get_status_by_camera(camera)


    def get_frames(self, ip: str):
        camera = self.camera_repository.find_by_ip(ip)
        if not camera.is_reachable():
            raise BadRequestException("Camera is not reachable")

        cap = cv2.VideoCapture(
            f"rtsp://{camera.username}:{camera.password}@{camera.ip}:{camera.port}/{camera.path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps / 2)  # 2 FPS will be enough
        frame_count = 0
        fixed_size = (640, 480)

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, fixed_size)
            if frame_count % frame_interval == 0:
                ret, buffer = cv2.imencode(".webp", frame)
                self.current_frames[ip] = buffer.tobytes()
            frame_count += 1


    def get_current_frame(self, ip: str):
        if self.current_frames.get(ip) is None:
            black_image = cv2.imencode('.webp', cv2.resize(cv2.imread(''), (640, 480)))[1].tobytes()
            return black_image
        else:
            return self.current_frames[ip]