import threading

import cv2

from app.models.camera import Camera
from app.models.recording import Recording


class RecordingThread(threading.Thread):
    def __init__(self, camera: Camera, recording: Recording):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.running = True


    def run(self):
        rtsp_url = f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}"
        file_path = f"{self.recording.path}/{self.recording.name}"

        cap = cv2.VideoCapture(rtsp_url)

        fps = cap.get(cv2.CAP_PROP_FPS)
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out = cv2.VideoWriter(file_path, cv2.VideoWriter.fourcc(*'vp80'), fps, (original_width, original_height))

        while self.running:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
            else:
                break

        cap.release()
        out.release()


    def stop(self):
        self.running = False
