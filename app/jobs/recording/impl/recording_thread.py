import io
import os
import subprocess
import threading
import time

import numpy as np

from PIL import Image

from app.models.camera import Camera
from app.models.recording import Recording


class RecordingThread(threading.Thread):
    def __init__(self, camera: Camera, recording: Recording):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.running = True
        self.file_path = os.path.join(recording.path, recording.name)
        self.current_frame = Image.fromarray(np.zeros((480, 640, 3), dtype=np.uint8)).tobytes()


    def run(self):
        command = [
            "ffmpeg",
            "-i",
            f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}",
            "-vf", "fps=4,scale=640:480",
            "-f", "image2pipe",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-c:v", "libvpx",
            "-b:v", "250k",
            "-preset", "ultrafast",
            "-cpu-used", "4",
            "-threads", "4",
            "-crf", "60",
            "-loglevel", "quiet",
            "-an",
            "-y", self.file_path,
            "-"
        ]

        proc = None
        is_unreachable = True

        while self.running:
            time.sleep(1) # check every second if process is still running

            try:
                if proc is None or is_unreachable or proc.poll() is not None:
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10 ** 8)
                    is_unreachable = False

                raw_frame = proc.stdout.read(640 * 480 * 3)
                frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((480, 640, 3))

                # convert frame to webp using numpy and pillow, it's lighter than using cv2
                image = Image.fromarray(frame)
                buffer = io.BytesIO()
                image.save(buffer, format="WEBP")
                blob = buffer.getvalue()

                self.current_frame = blob

            except Exception as e:
                is_unreachable = True
                print("Exception on recording thread:", e)

        if proc is not None:
            proc.terminate()


    def stop(self):
        self.running = False


    def get_current_frame(self):
        return self.current_frame