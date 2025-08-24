import os
import threading
import time
import cv2
import numpy as np
from datetime import datetime

from app.models.camera import Camera
from app.models.recording import Recording


class RecordingThread(threading.Thread):
    def __init__(self, camera: 'Camera', recording: 'Recording', on_error_callback):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.on_error_callback = on_error_callback
        self.file_path = os.path.join(recording.path, recording.name)
        self.running = None
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.fps = 4.0
        self.frame_width = 1920
        self.frame_height = 1080
        self.reconnect_delay = 5
        self.max_reconnect_delay = 30
        self.frame_timeout = 10.0

    def run(self):
        self.running = True
        input_url = f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}"

        cap = None
        writer = None
        last_frame_time = time.time()
        reconnect_delay = self.reconnect_delay
        black_frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        frame_interval = 1.0 / self.fps
        last_write_time = 0
        disconnected = False

        try:
            while self.running:
                if cap is None or not cap.isOpened():
                    if cap is not None:
                        cap.release()

                    cap = cv2.VideoCapture(input_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, self.fps)

                    if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))

                    if not cap.isOpened():
                        if self.running:
                            time.sleep(reconnect_delay)
                            reconnect_delay = min(reconnect_delay * 2, self.max_reconnect_delay)
                        continue

                    reconnect_delay = self.reconnect_delay

                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self.frame_height, self.frame_width = frame.shape[:2]
                        black_frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)

                    if writer is None:
                        writer = cv2.VideoWriter(
                            self.file_path,
                            self.fourcc,
                            self.fps,
                            (self.frame_width, self.frame_height)
                        )

                    disconnected = False

                ret, frame = cap.read()
                current_time = time.time()

                if ret and frame is not None:
                    last_frame_time = current_time

                    if current_time - last_write_time >= frame_interval:
                        writer.write(frame)
                        last_write_time = current_time

                    disconnected = False
                else:
                    if current_time - last_frame_time > self.frame_timeout:
                        if cap is not None:
                            cap.release()
                            cap = None

                        if not disconnected:
                            print(f"Connection lost for camera {self.camera.ip}")
                            disconnected = True

                    if current_time - last_write_time >= frame_interval:
                        if writer is not None:
                            writer.write(black_frame)
                        last_write_time = current_time

                    time.sleep(0.01)

        except Exception as e:
            print(f"Error in recording thread: {e}")
            if self.running:
                self.on_error_callback(self.recording)

        finally:
            if cap is not None:
                cap.release()
            if writer is not None:
                writer.release()
            self.running = None

    def stop(self):
        if self.running is not None:
            self.running = False
            while self.running is not None:
                time.sleep(0.1)