import os
import subprocess
import threading
import time

from app.models.camera import Camera
from app.models.recording import Recording


class RecordingThread(threading.Thread):
    def __init__(self, camera: Camera, recording: Recording):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.running = True
        self.file_path = os.path.join(recording.path, recording.name)
        self.proc = None


    def run(self):
        command = [
            "ffmpeg",
            "-i",
            f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}",
            "-vf", "fps=4",
            "-c:v", "libvpx",
            "-b:v", "500k",
            "-preset", "ultrafast",
            "-cpu-used", "4",
            "-threads", "4",
            "-crf", "60",
            '-loglevel', 'quiet',
            "-an",
            self.file_path
        ]

        is_unreachable = True

        while self.running:
            time.sleep(1) # check every second if process is still running

            try:
                if self.proc is None or is_unreachable or self.proc.poll() is not None:
                    is_unreachable = False
                    self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10 ** 8)
            except Exception as e:
                is_unreachable = True
                print("Exception on recording thread:", e)

        if self.proc is not None:
            self.proc.terminate()


    def stop(self):
        self.running = False
        if self.proc is not None:
            self.proc.terminate()
