import io
import subprocess
import threading
import time
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


class CameraListenerThread(threading.Thread):
    def __init__(self, camera: Camera, callback: Callable[[Camera, CameraStatus, bytes | None], None]):
        super().__init__()
        self.camera = camera
        self.callback = callback
        self.running = True
        self.current_status = CameraStatus.UNREACHABLE # so that it will try to connect on first run
        self.current_frame = cv2.imencode('.webp', cv2.resize(cv2.UMat(480, 640, cv2.CV_8UC3, (0, 0, 0)).get(), (640, 480)))[1].tobytes()


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

        proc = None
        last_greyscale_frame = None

        while self.running:
            time.sleep(1) # check every second if process is still running

            try:
                if proc is None or self.current_status == CameraStatus.UNREACHABLE or proc.poll() is not None:
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10 ** 8)
                    self.set_and_post_status(CameraStatus.IDLE)

                raw_frame = proc.stdout.read(640 * 480 * 3)
                frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((480, 640, 3))

                # convert frame to webp using numpy and pillow, it's lighter than using cv2
                image = Image.fromarray(frame)
                buffer = io.BytesIO()
                image.save(buffer, format="WEBP")
                blob = buffer.getvalue()
                self.current_frame = blob

                # only do motion detection if camera is listening
                if self.camera.listening:
                    frame = cv2.resize(frame, (640, 480))
                    frame_area = frame.shape[0] * frame.shape[1]

                    # ensure we start with a last frame set
                    if last_greyscale_frame is None:
                        last_greyscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        last_greyscale_frame = cv2.GaussianBlur(last_greyscale_frame, (21, 21), 0)
                        last_greyscale_frame = last_greyscale_frame
                        continue

                    current_grayscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    current_grayscale_frame = cv2.GaussianBlur(current_grayscale_frame, (21, 21), 0)

                    diff = cv2.absdiff(last_greyscale_frame, current_grayscale_frame)
                    _, thresh = cv2.threshold(diff, 15, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    # combine all contours in one rectangle and check if big enough
                    if contours:
                        x_min, y_min = float('inf'), float('inf')
                        x_max, y_max = float('-inf'), float('-inf')

                        for contour in contours:
                            x, y, w, h = cv2.boundingRect(contour)
                            x_min = min(x_min, x)
                            y_min = min(y_min, y)
                            x_max = max(x_max, x + w)
                            y_max = max(y_max, y + h)

                        combined_rect_area = (x_max - x_min) * (y_max - y_min)

                        if combined_rect_area > (1 - self.camera.sensibility / 100) * frame_area:
                            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                            _, jpeg = cv2.imencode('.jpg', frame)
                            blob = jpeg.tobytes()

                            self.set_and_post_status(CameraStatus.MOVEMENT_DETECTED, blob)

                    last_greyscale_frame = current_grayscale_frame

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
