import threading
import time
from typing import Callable

import cv2

from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


class CameraListenerThread(threading.Thread):
    def __init__(self, camera: Camera, callback: Callable[[Camera, CameraStatus], None]):
        super().__init__()
        self.wait_between_frames = 0.5
        self.camera = camera
        self.callback = callback
        self.running = True
        self.previous_status = CameraStatus.IDLE
        self.frame_count = 0
        self.movement_frames = 0


    def run(self):
        cap = cv2.VideoCapture(
            f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}")
        first_frame = None

        while self.running:
            if not self.camera.is_reachable():
                self.callback(self.camera, CameraStatus.UNREACHABLE)
                self.previous_status = CameraStatus.UNREACHABLE
                time.sleep(self.wait_between_frames)
                continue

            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.resize(frame, (640, 480))

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if first_frame is None:
                first_frame = gray
                time.sleep(self.wait_between_frames)
                continue

            frame_delta = cv2.absdiff(first_frame, gray)
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            thresh = cv2.dilate(thresh, kernel, iterations=2)
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            movement_detected = False
            for contour in contours:
                if cv2.contourArea(contour) < (0.2 * frame.shape[0] * frame.shape[1]):
                    continue
                movement_detected = True
                break

            if movement_detected:
                self.movement_frames += 1
            else:
                self.movement_frames = 0

            if self.movement_frames >= 4:
                current_status = CameraStatus.MOVEMENT_DETECTED
            else:
                current_status = CameraStatus.IDLE

            if current_status != self.previous_status:
                self.callback(self.camera, current_status)
                self.previous_status = current_status

            time.sleep(self.wait_between_frames)

        cap.release()


    def stop(self):
        self.running = False
