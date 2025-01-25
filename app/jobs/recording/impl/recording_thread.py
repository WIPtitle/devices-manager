import asyncio
import os
import subprocess
import threading
import time

from ffmpeg import Progress
from ffmpeg.asyncio import FFmpeg

from app.models.camera import Camera
from app.models.recording import Recording

'''
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
'''

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
                rtsp_transport="tcp",
                rtsp_flags="prefer_tcp",
            )
            .output(self.file_path, vcodec="copy")
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
