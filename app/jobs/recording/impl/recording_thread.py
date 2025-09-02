import os
import threading
import subprocess
import time

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

    def run(self):
        self.running = True
        try:
            input_url = f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}"

            if self.camera.always_recording:
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-rtsp_transport", "tcp",
                    "-i", input_url,
                    "-c:v", "copy",
                    "-f", "matroska",
                    "-avoid_negative_ts", "make_zero",
                    "-use_wallclock_as_timestamps", "1",
                    "-loglevel", "warning",
                    self.file_path
                ]
            else:
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-rtsp_transport", "tcp",
                    "-i", input_url,
                    "-t", "120",
                    "-c:v", "copy",
                    "-f", "matroska",
                    "-avoid_negative_ts", "make_zero",
                    "-loglevel", "warning",
                    self.file_path
                ]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            while True:
                return_code = proc.poll()
                if return_code is not None:
                    if return_code != 0 and self.running:
                        self.on_error_callback(self.recording)
                    break

                if not self.running:
                    proc.terminate()
                    proc.wait()
                    break

                time.sleep(0.1)

        except Exception as e:
            print(f"Error in recording thread: {e}")
            if self.running:
                self.on_error_callback(self.recording)

        finally:
            self.running = None

    def stop(self):
        if self.running is not None:
            self.running = False
            while self.running is not None:
                time.sleep(0.1)