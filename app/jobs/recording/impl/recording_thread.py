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

            cmd = [
                "ffmpeg",
                "-y",
                "-rtsp_transport", "tcp",
                "-timeout", "20000000",
                "-use_wallclock_as_timestamps", "1",
                "-fflags", "+genpts+discardcorrupt",
                "-i", input_url,
                "-rw_timeout", "20000000",
                "-reconnect", "1",
                "-reconnect_at_eof", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "20",
                "-vcodec", "libx264",
                "-vf", "fps=4,setpts=if(eq(N\\,0)\\,0\\,PTS+1/(4*TB))",
                "-preset", "fast",
                "-an",
                "-fps_mode", "passthrough",
                "-f", "matroska",
                "-copytb", "1",
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
                    # Process exited
                    if return_code != 0 and self.running:
                        self.on_error_callback(self.recording)
                    break

                if not self.running:
                    # Signal termination
                    proc.terminate()
                    # Wait for process to finish
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
            # Wait until thread cleans up
            while self.running is not None:
                time.sleep(0.1)