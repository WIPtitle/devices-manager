import sys
from typing import Dict

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient

from app.exceptions.cameras_listener_exception import CamerasListenerException
from app.jobs.cameras_listener import CamerasListener
from app.jobs.impl.camera_listener_thread import CameraListenerThread
from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


class CamerasListenerImpl(CamerasListener):
    def __init__(self, rabbitmq_client: RabbitMQClient):
        self.rabbitmq_client = rabbitmq_client
        self.cameras_status: Dict[Camera, CameraStatus] = {}
        self.threads = []


    def add_camera(self, camera: Camera):
        if camera not in self.cameras_status:
            # Set default first status to idle, listener thread will update it with the correct one once started.
            self.cameras_status[camera] = CameraStatus.IDLE
            thread = CameraListenerThread(camera, self.update_status)
            thread.start()
            self.threads.append(thread)
        else:
            raise CamerasListenerException(f"Camera with ip {camera.ip} already being monitored")


    def update_camera(self, camera: Camera):
        for c in list(self.cameras_status.keys()):
            if c.ip == camera.ip:
                self.remove_camera(c)
                self.add_camera(camera)
                return
        raise CamerasListenerException(f"Camera with ip {camera.ip} not being monitored")


    def remove_camera(self, camera: Camera):
        if camera in self.cameras_status:
            for thread in self.threads:
                if thread.camera.ip == camera.ip:
                    thread.stop()
                    self.threads.remove(thread)
                    break
            del self.cameras_status[camera]
        else:
            raise CamerasListenerException(f"Camera with ip {camera.ip} not being monitored")


    def get_status_by_camera(self, camera: Camera) -> CameraStatus:
        if camera in self.cameras_status:
            return self.cameras_status[camera]
        else:
            raise CamerasListenerException(f"Camera with ip {camera.ip} not being monitored")


    def update_status(self, camera: Camera, status: CameraStatus, blob: bytes | None = None):
        # Status changed, emit event; status changed control should happen in thread instead of bombarding this
        # callback with statuses for each frame.
        self.cameras_status[camera] = status
        print(f"Changed status for camera {camera.ip}: {status.value}")
        sys.stdout.flush()
        #TODO should publish event here once it is working
        # like this -> self.rabbitmq_client.publish(CameraChangedStatus(camera.ip, RabbitCameraStatus.IDLE))
