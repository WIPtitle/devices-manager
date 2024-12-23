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


class CameraListenerThread(threading.Thread):
    def __init__(self, camera: Camera, callback: Callable[[Camera, CameraStatus, bytes | None], None]):
        super().__init__()
        self.camera = camera
        self.callback = callback
        self.running = True
        self.predicting = False
        self.current_status = CameraStatus.UNREACHABLE # so that it will try to connect on first run
        self.current_frame = cv2.imencode('.webp', cv2.resize(cv2.UMat(480, 640, cv2.CV_8UC3, (0, 0, 0)).get(), (640, 480)))[1].tobytes()
        self.listening_fps = 4


    def run(self):
        while self.running:
            if self.current_status == CameraStatus.UNREACHABLE:
                cap = cv2.VideoCapture(
                    f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}")

                if not cap.isOpened():
                    self.set_and_post_status(CameraStatus.UNREACHABLE)
                    continue

                camera_fps = cap.get(cv2.CAP_PROP_FPS)

            try:
                # sleep for a while to match the listening fps, grabbing but not loading the frames to return always the latest
                sleep(1 / self.listening_fps)
                for _ in range(int(camera_fps / self.listening_fps) - 1):
                    cap.grab()

                # read frame
                ret, frame = cap.read()
                if not ret:
                    self.set_and_post_status(CameraStatus.UNREACHABLE)
                    continue

                frame = cv2.resize(frame, (640, 480))

                ret_fr, buffer_fr = cv2.imencode(".webp", frame)
                self.current_frame = buffer_fr.tobytes()

                # only detect human if listening and not already detecting
                # running in separate thread so it doesn't block the camera listener from reading frames,
                # since predict can take a while
                if self.camera.listening and not self.predicting:
                    threading.Thread(target=self.run_predict, args=(frame,)).start()

                self.set_and_post_status(CameraStatus.IDLE)

            except Exception as e:
                print("Exception on camera listener:", e)
                self.set_and_post_status(CameraStatus.UNREACHABLE)
                continue

        cap.release()


    def run_predict(self, frame):
        self.predicting = True
        try:
            results = model.predict(frame)
            confidence_threshold = 0.6 - (self.camera.sensibility / 100) * 0.2 # 0.4 to 0.6 with respectively 100 to 0 sensibility, using 0.5 as the base threshold

            # get the largest human box to draw on the frame given the results and a threshold
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

            if largest_box is not None:
                x1, y1, x2, y2 = map(int, largest_box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Save blob on first frame, discard it if movement not continuous
                _, jpeg = cv2.imencode('.jpg', frame)
                blob = jpeg.tobytes()

                self.set_and_post_status(CameraStatus.MOVEMENT_DETECTED, blob)
        except Exception as e:
            print("Exception on camera listener human detection:", e)
            self.predicting = False
        finally:
            self.predicting = False


    def set_and_post_status(self, status: CameraStatus, blob: bytes | None = None):
        if self.current_status != status:
            self.current_status = status
            self.callback(self.camera, status, blob)


    def get_current_frame(self):
        return self.current_frame


    def stop(self):
        self.running = False
