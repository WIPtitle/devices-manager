import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class FFmpegStreamer:
    def __init__(self, camera):
        self.camera = camera
        self.process = None
        self.running = False

    async def generate_stream(self) -> AsyncGenerator[bytes, None]:
        rtsp_url = f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}"

        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c:v", "copy",
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "-frag_duration", "1000000",
            "-"
        ]

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )

        self.running = True

        try:
            while self.running:
                chunk = await self.process.stdout.read(65536)
                if not chunk:
                    break
                yield chunk

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

        streamer = FFmpegStreamer(camera)
        self.streamers[stream_key] = streamer

        try:
            async for chunk in streamer.generate_stream():
                yield chunk
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