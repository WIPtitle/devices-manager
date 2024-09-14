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
        frames_with_movement = 0

        while self.running:
            try:
                # Do NOT use camera.is_reachable() here since it is a heavy operation and we do NOT want to slow down
                # this cycle.
                if not cap.isOpened():
                    self.set_and_post_status(CameraStatus.UNREACHABLE)
                    continue

                ret, frame = cap.read()
                if not ret:
                    self.set_and_post_status(CameraStatus.UNREACHABLE)
                    continue

                # Process only one frame every five. This is kind of a "magic" number since I don't let users
                # set it, but most cameras will have no framerate too low problem.
                frame_counter = (frame_counter + 1) % 5
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
                    if merged_area > self.camera.sensibility / 100 * frame_area:
                        frames_with_movement += 1
                        # We consider it movement only if there is movement for at least 3 consecutive frames, otherwise
                        # we discard it as noise
                        if frames_with_movement >= 3:
                            _, jpeg = cv2.imencode('.jpg', frame)
                            blob = jpeg.tobytes()
                            self.set_and_post_status(CameraStatus.MOVEMENT_DETECTED, blob)
                            continue
                    else:
                        frames_with_movement = 0
                else:
                    frames_with_movement = 0

                # If we reach the end it means no movement big enough was found so camera returns in idle status
                self.set_and_post_status(CameraStatus.IDLE)

            except:
                self.set_and_post_status(CameraStatus.UNREACHABLE)
                continue

        cap.release()


    def set_and_post_status(self, status: CameraStatus, blob: bytes | None = None):
        if self.current_status != status:
            self.current_status = status
            self.callback(self.camera, status, blob)


    def stop(self):
        self.running = False
