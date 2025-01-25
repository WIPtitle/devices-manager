import asyncio
import os
import subprocess
import threading
import time

from ffmpeg import Progress
from ffmpeg.asyncio import FFmpeg

from app.models.camera import Camera
from app.models.recording import Recording


class RecordingThread(threading.Thread):
    def __init__(self, camera: Camera, recording: Recording):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.file_path = os.path.join(recording.path, recording.name)
        self.running = None


    async def start_ffmpeg(self):
        ffmpeg = (
            FFmpeg()
            .option("y")
            .input(
                f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}",
                rtsp_transport="udp",
            )
            .output(self.file_path, vcodec="libx264", vf="fps=4", preset="fast", an=None)
        )

        @ffmpeg.on("progress")
        def time_to_terminate(progress: Progress):
            if self.running is not None and self.running == False:
                ffmpeg.terminate()

        await ffmpeg.execute()


    def run(self):
        self.running = True
        asyncio.run(self.start_ffmpeg())


    def stop(self):
        self.running = False
