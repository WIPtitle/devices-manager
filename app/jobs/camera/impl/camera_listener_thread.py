import logging
import threading
from time import sleep
from typing import Callable

import cv2
from ultralytics import YOLO

from app.models.camera import Camera
from app.models.enums.camera_status import CameraStatus


logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.ERROR)

# Load YOLO model
model = YOLO('yolo11s-pose.pt')

# returns largest human box to draw on the frame given the results and a threshold, or None if human is not found
def get_human_box(results, confidence_threshold):
    max_area = 0
    largest_box = None
    for result in results:
        boxes = result.boxes
        keypoints = result.keypoints

        if keypoints is not None:
            for box in boxes:
                cls = int(box.cls[0])
                conf = box.conf[0]
                if cls == 0 and conf >= confidence_threshold:  # 0 is the label for human
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2 - x1) * (y2 - y1)
                    if area > max_area:
                        max_area = area
                        largest_box = box
    return largest_box


class CameraListenerThread(threading.Thread):
    def __init__(self, camera: Camera, callback: Callable[[Camera, CameraStatus, bytes | None], None]):
        super().__init__()
        self.camera = camera
        self.callback = callback
        self.running = True
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
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_interval = int(fps / 2)  # 2 FPS will be enough
                frame_count = 0
                frames_with_human = 0

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

                self.set_and_post_status(CameraStatus.IDLE)

                # Process only one frame every frame interval, this weights less on the machine and movement can still be
                # found at 2 FPS
                frame_count += 1
                if frame_count % frame_interval == 0:
                    frame_count = 0
                    frame = cv2.resize(frame, (640, 480))

                    ret_fr, buffer_fr = cv2.imencode(".webp", frame)
                    self.current_frame = buffer_fr.tobytes()

                    results = model.predict(frame)
                    human_box = get_human_box(results, 1 - (self.camera.sensibility / 100))
                    if human_box is not None:
                        frames_with_human += 1

                        if frames_with_human == 1:
                            x1, y1, x2, y2 = map(int, human_box.xyxy[0])
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                            # Save blob on first frame, discard it if movement not continuous
                            _, jpeg = cv2.imencode('.jpg', frame)
                            blob = jpeg.tobytes()

                        # We consider it movement only if there is a human for at least 4 consecutive frames (2s), otherwise
                        # we discard it as noise
                        if frames_with_human >= 4:
                            self.set_and_post_status(CameraStatus.MOVEMENT_DETECTED, blob)
                    else:
                        frames_with_human = 0
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
