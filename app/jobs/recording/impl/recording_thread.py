import asyncio
import os
import threading
import time

from ffmpeg import Progress
from ffmpeg.asyncio import FFmpeg

from app.models.camera import Camera
from app.models.recording import Recording


class RecordingThread(threading.Thread):
    def __init__(self, camera: Camera, recording: Recording, on_error_callback):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.on_error_callback = on_error_callback
        self.file_path = os.path.join(recording.path, recording.name)
        self.running = None

    async def start_ffmpeg(self):
        try:
            ffmpeg = (
                FFmpeg()
                .option("y")
                .input(
                    f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}",
                    rtsp_transport="tcp",
                    **{
                        "stimeout": "10000000",  # 10-second timeout (allows short outages)
                        "use_wallclock_as_timestamps": "1",
                        "reconnect": "1",  # Basic reconnection
                        "reconnect_on_network_error": "1",  # Explicitly handle network issues
                        "reconnect_at_eof": "1",  # Reconnect even if stream "ends"
                        "reconnect_delay_max": "30",  # Max 30s between attempts
                    }
                )
                .output(
                    self.file_path,
                    vcodec="libx264",
                    vf="fps=4",
                    preset="fast",
                    an=None,
                    reset_timestamps=1,
                    f="matroska",
                    cluster_time_limit=5000,
                    **{
                        "vsync": "0",  # Critical for frame duplication fix
                        "copytb": "1",  # Preserve source timebase
                        "t": "120",  # Max 2-minute recording (even with reconnects)
                    }
                )
            )

            @ffmpeg.on("progress")
            def time_to_terminate(progress: Progress):
                if self.running is not None and not self.running:
                    ffmpeg.terminate()
                    self.running = None

            await ffmpeg.execute()

        except Exception as e:
            print("Error from FFmpeg:", e)
            self.on_error_callback(self.recording)


    def run(self):
        self.running = True
        asyncio.run(self.start_ffmpeg())


    def stop(self):
        self.running = False
        while self.running is not None:
            time.sleep(0.1)
