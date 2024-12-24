import os
import subprocess
import threading

from app.models.camera import Camera
from app.models.recording import Recording


def get_unique_file_path(base_path):
    file_path = base_path
    file_root, file_ext = os.path.splitext(base_path)
    counter = 1
    while os.path.exists(file_path):
        file_path = f"{file_root}({counter}){file_ext}"
        counter += 1
    return file_path


class RecordingThread(threading.Thread):
    def __init__(self, camera: Camera, recording: Recording):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.running = True
        self.file_path = get_unique_file_path(f"{self.recording.path}/{self.recording.name}.webm")


    def run(self):
        command = [
            "ffmpeg",
            "-i", self.camera.url,
            "-vf", "fps=5",
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


