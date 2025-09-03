import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class FFmpegMJPEGStreamer:
    def __init__(self, camera):
        self.camera = camera
        self.process = None
        self.running = False

    async def generate_frames(self) -> AsyncGenerator[bytes, None]:
        rtsp_url = f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}"

        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-r", "15",
            "-s", "1280x720",
            "-q:v", "5",
            "-f", "mjpeg",
            "-"
        ]

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )

        self.running = True
        buffer = b''

        try:
            while self.running:
                chunk = await self.process.stdout.read(65536)
                if not chunk:
                    break

                buffer += chunk

                while True:
                    start = buffer.find(b'\xff\xd8')
                    if start == -1:
                        break

                    end = buffer.find(b'\xff\xd9', start + 2)
                    if end == -1:
                        break

                    jpeg = buffer[start:end + 2]
                    buffer = buffer[end + 2:]

                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')

        except Exception as e:
            logger.error(f"Stream error for {self.camera.ip}: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        self.running = False
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
            self.process = None


class FFmpegStreamManager:
    def __init__(self):
        self.streamers = {}

    async def get_stream(self, camera) -> AsyncGenerator[bytes, None]:
        stream_key = camera.ip

        if stream_key in self.streamers:
            self.streamers[stream_key].cleanup()

        streamer = FFmpegMJPEGStreamer(camera)
        self.streamers[stream_key] = streamer

        try:
            async for frame in streamer.generate_frames():
                yield frame
        finally:
            if stream_key in self.streamers and self.streamers[stream_key] == streamer:
                del self.streamers[stream_key]

    def cleanup_stream(self, camera_ip: str):
        if camera_ip in self.streamers:
            self.streamers[camera_ip].cleanup()
            del self.streamers[camera_ip]

    def cleanup_all(self):
        for streamer in self.streamers.values():
            streamer.cleanup()
        self.streamers.clear()