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


    def run(self):
        command = [
            "ffmpeg",
            "-i", f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}",
            "-vf", "fps=4",
            "-c:v", "libvpx",
            "-b:v", "250k",
            "-preset", "ultrafast",
            "-cpu-used", "4",
            "-threads", "4",
            "-crf", "60",
            '-loglevel', 'quiet',
            "-an",
            self.file_path
        ]

        proc = None
        is_unreachable = True

        while self.running:
            time.sleep(1) # check every second if process is still running

            try:
                if proc is None or is_unreachable or proc.poll() is not None:
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10 ** 8)
                    is_unreachable = False
            except Exception as e:
                is_unreachable = True
                print("Exception on recording thread:", e)

        if proc is not None:
            proc.terminate()


    def stop(self):
        self.running = False


