import os
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

        is_unreachable = True

        while self.running:
            if is_unreachable:
                cap = cv2.VideoCapture(rtsp_url)
                if not cap.isOpened():
                    continue

                fps = cap.get(cv2.CAP_PROP_FPS)
                original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # output stream is redefined with existing frames if it already exists, to avoid overriding if camera unreachable and then restarts
                if os.path.exists(file_path):
                    existing_cap = cv2.VideoCapture(file_path)
                    out = cv2.VideoWriter(file_path, cv2.VideoWriter.fourcc(*'vp80'), fps, (original_width, original_height))
                    while existing_cap.isOpened():
                        ret, frame = existing_cap.read()
                        if not ret:
                            break
                        out.write(frame)
                    existing_cap.release()
                else:
                    out = cv2.VideoWriter(file_path, cv2.VideoWriter.fourcc(*'vp80'), fps, (original_width, original_height))

            try:
                ret, frame = cap.read()
                if ret:
                    out.write(frame)
                    is_unreachable = False
                else:
                    is_unreachable = True
            except Exception as e:
                print("Exception on recording:", e)
                is_unreachable = True

        cap.release()
        out.release()


    def stop(self):
        self.running = False
