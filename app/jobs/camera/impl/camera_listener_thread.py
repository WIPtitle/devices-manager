import subprocess
import threading
from typing import Callable
import io

import numpy as np
from PIL import Image

from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


def motion_detection(frame1, frame2, threshold_percentage):
    if frame1 is None or frame2 is None:
        return False
    diff = np.abs(frame1.astype(np.int16) - frame2.astype(np.int16))
    diff = np.mean(diff, axis=2)
    diff_bin = (diff > 0).astype(np.uint8)
    changed_pixels = np.sum(diff_bin)
    total_pixels = diff_bin.size
    changed_percentage = (changed_pixels / total_pixels) * 100
    return changed_percentage > threshold_percentage


class CameraListenerThread(threading.Thread):
    def __init__(self, camera: Camera, callback: Callable[[Camera, CameraStatus, bytes | None], None]):
        super().__init__()
        self.camera = camera
        self.callback = callback
        self.running = True
        self.current_status = CameraStatus.UNREACHABLE # so that it will try to connect on first run
        self.current_frame = np.zeros((480, 640, 3), dtype=np.uint8).tobytes()


    def run(self):
        command = [
            "ffmpeg",
            "-i", f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}",
            "-vf", "fps=1,scale=640:480",
            "-f", "image2pipe",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            '-loglevel', 'quiet',
            "-"
        ]

        frames_with_movement = 0
        prev_frame = None
        proc = None

        while self.running:
            try:
                if proc is None or self.current_status == CameraStatus.UNREACHABLE or proc.poll() is not None:
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10 ** 8)
                    self.set_and_post_status(CameraStatus.IDLE)

                raw_frame = proc.stdout.read()
                curr_frame = np.frombuffer(raw_frame, dtype=np.uint8)

                image = Image.fromarray(curr_frame)
                buffer = io.BytesIO()
                image.save(buffer, format="WEBP")
                blob = buffer.getvalue()
                self.current_frame = blob

                if motion_detection(prev_frame, curr_frame, 100 - self.camera.sensibility):
                    frames_with_movement += 1

                if frames_with_movement == 2:
                    image = Image.fromarray(curr_frame)
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG")
                    blob = buffer.getvalue()

                    self.set_and_post_status(CameraStatus.MOVEMENT_DETECTED, blob)
                    frames_with_movement = 0

                prev_frame = curr_frame
            except Exception as e:
                print("Exception on camera listener:", e)
                self.set_and_post_status(CameraStatus.UNREACHABLE)

        if proc is not None:
            proc.terminate()


    def set_and_post_status(self, status: CameraStatus, blob: bytes | None = None):
        if self.current_status != status:
            self.current_status = status
            self.callback(self.camera, status, blob)


    def get_current_frame(self):
        return self.current_frame


    def stop(self):
        self.running = False
