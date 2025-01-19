from app.jobs.camera.camera_stream_manager import CameraStreamManager
from app.jobs.camera.impl.camera_stream_thread import CameraStreamThread
from app.models.camera import Camera


class CameraStreamManagerImpl(CameraStreamManager):
    def __init__(self):
        self.threads = []


    def start_streaming(self, camera: Camera):
        thread = CameraStreamThread(camera)
        thread.start()
        self.threads.append(thread)
        print(f"Start streaming for camera on {camera.ip}")


    def stop_streaming(self, camera: Camera):
        for thread in self.threads:
            if thread.camera.ip == camera.ip:
                thread.stop()
                self.threads.remove(thread)
                break
        print(f"Stopped streaming for camera on {camera.ip}")