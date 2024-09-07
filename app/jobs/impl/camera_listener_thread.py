import sys
import threading
from typing import Callable

import cv2

from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


class CameraListenerThread(threading.Thread):
    def __init__(self, camera: Camera, callback: Callable[[Camera, CameraStatus, bytes | None], None]):
        super().__init__()
        self.camera = camera
        self.callback = callback
        self.running = True
        self.frame_count = 0
        self.movement_frames = 0
        self.current_status = CameraStatus.IDLE


    def run(self):
        cap = cv2.VideoCapture(
            f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}")
        fgbg = cv2.createBackgroundSubtractorMOG2()
        frame_counter = 0
        counter = 0

        while self.running:
            print(f"running {counter}")
            counter += 1
            sys.stdout.flush()
            if not self.camera.is_reachable() and self.current_status != CameraStatus.UNREACHABLE:
                self.current_status = CameraStatus.UNREACHABLE
                self.callback(self.camera, CameraStatus.UNREACHABLE, None)
                continue

            ret, frame = cap.read()
            if ret:
                # Process only one frame every four. This is kind of a "magic" number since I don't let users
                # set it, but most cameras will have no framerate too low problem.
                frame_counter = (frame_counter + 1) % 4
                if frame_counter != 0:
                    continue

                frame = cv2.resize(frame, (640, 480))
                frame_area = frame.shape[0] * frame.shape[1]

                fgmask = fgbg.apply(frame)
                contours, _ = cv2.findContours(fgmask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                rects = []
                for contour in contours[1:]:
                    # We consider a movement to be real if at least 2% of camera area, if less it will be discarded as noise
                    if cv2.contourArea(contour) > 0.02 * frame_area:
                        (x, y, w, h) = cv2.boundingRect(contour)
                        rects.append((x, y, w, h))

                # Merge small rectangles
                if rects:
                    x_min = min([x for (x, y, w, h) in rects])
                    y_min = min([y for (x, y, w, h) in rects])
                    x_max = max([x + w for (x, y, w, h) in rects])
                    y_max = max([y + h for (x, y, w, h) in rects])
                    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

                    merged_area = (x_max - x_min) * (y_max - y_min)
                    print(merged_area)
                    print(self.camera.sensibility / 100 * frame_area)
                    if (merged_area > self.camera.sensibility / 100 * frame_area) and self.current_status != CameraStatus.MOVEMENT_DETECTED:
                        print(f"Changed status for camera")
                        sys.stdout.flush()
                        # Enough movement found
                        _, jpeg = cv2.imencode('.jpg', frame)
                        blob = jpeg.tobytes()

                        self.current_status = CameraStatus.MOVEMENT_DETECTED
                        self.callback(self.camera, CameraStatus.MOVEMENT_DETECTED, blob)
                        continue

                # If we reach the end it means no movement big enough was found so camera returns in idle status
                if self.current_status != CameraStatus.IDLE:
                    self.current_status = CameraStatus.IDLE
                    self.callback(self.camera, CameraStatus.IDLE, None)

        cap.release()


    def stop(self):
        self.running = False
