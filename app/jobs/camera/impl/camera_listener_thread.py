import threading
from time import sleep
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
        self.current_status = CameraStatus.UNREACHABLE # so that it will try to connect on first run
        self.current_frame = cv2.imencode('.webp', cv2.resize(cv2.UMat(480, 640, cv2.CV_8UC3, (0, 0, 0)).get(), (640, 480)))[1].tobytes()


    def run(self):
        global blob

        while self.running:
            if self.current_status == CameraStatus.UNREACHABLE:
                print("Camera unreachable, trying again in 5 seconds")
                sleep(5)

                cap = cv2.VideoCapture(
                    f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}")
                fgbg = cv2.createBackgroundSubtractorMOG2()
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_interval = int(fps / 2)  # 2 FPS will be enough
                frame_count = 0
                frames_with_movement = 0
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

                # Process only one frame every frame interval, this weights less on the machine and movement can still be
                # found at 2 FPS
                if frame_count % frame_interval == 0:
                    frame = cv2.resize(frame, (640, 480))
                    frame_area = frame.shape[0] * frame.shape[1]

                    ret_fr, buffer_fr = cv2.imencode(".webp", frame)
                    self.current_frame = buffer_fr.tobytes()

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
                            if frames_with_movement == 1:
                                # Save blob on first frame, send it on third or discard it if movement not continuous
                                _, jpeg = cv2.imencode('.jpg', frame)
                                blob = jpeg.tobytes()
                            # We consider it movement only if there is movement for at least 4 consecutive frames (2s), otherwise
                            # we discard it as noise
                            if frames_with_movement >= 4:
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


    def get_current_frame(self):
        return self.current_frame


    def stop(self):
        self.running = False
