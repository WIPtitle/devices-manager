import io
import subprocess
import threading
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


def find_biggest_rectangle(contours):
    largest_rect = None
    largest_area = 0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area > largest_area:
            largest_area = area
            largest_rect = (x, y, w, h)

    return largest_rect


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
            "-hwaccel", "auto",
            "-i", f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}",
            "-vf", "fps=1,scale=640:480",
            "-f", "image2pipe",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            '-loglevel', 'quiet',
            "-"
        ]

        proc = None

        while self.running:
            try:
                if proc is None or self.current_status == CameraStatus.UNREACHABLE or proc.poll() is not None:
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10 ** 8)
                    fgbg = cv2.createBackgroundSubtractorMOG2()

                    self.set_and_post_status(CameraStatus.IDLE)
                    frames_with_movement = 0

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

                    fgmask = fgbg.apply(frame)
                    contours, _ = cv2.findContours(fgmask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                    filtered_contours = [contour for contour in contours if cv2.contourArea(contour) > self.camera.sensibility / 100 * frame_area]
                    rectangle = find_biggest_rectangle(filtered_contours)

                    # if there is movement bigger than threshold keep the biggest rectangle
                    if rectangle:
                        frames_with_movement += 1

                        # if there is movement for 2 frames in a row, consider it as movement detected
                        if frames_with_movement == 2:
                            x, y, w, h = rectangle
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            _, jpeg = cv2.imencode('.jpg', frame)
                            blob = jpeg.tobytes()

                            self.set_and_post_status(CameraStatus.MOVEMENT_DETECTED, blob)
                            frames_with_movement = 0
                    else:
                        frames_with_movement = 0

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
