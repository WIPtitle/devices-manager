import time
import os
import subprocess
import asyncio
from typing import Sequence

from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from app.config.bindings import inject
from app.models.camera import Camera, CameraInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.camera.camera_service import CameraService


class CameraRouter(RouterWrapper):
    @inject
    def __init__(self, camera_service: CameraService):
        super().__init__(prefix=f"/camera")
        self.camera_service = camera_service

    def _define_routes(self):
        # Basic CRUD
        @self.router.get("/{ip}")
        def get_camera_by_ip(ip: str) -> Camera:
            return self.camera_service.get_by_ip(ip)

        @self.router.post("/", operation_id="create_camera_slash")
        @self.router.post("", operation_id="create_camera_without_slash")
        def create_camera(camera: CameraInputDto) -> Camera:
            return self.camera_service.create(Camera.from_dto(camera))

        @self.router.delete("/{ip}")
        def delete_camera_by_ip(ip: str) -> Camera:
            return self.camera_service.delete_by_ip(ip)

        @self.router.get("/")
        def get_all_cameras() -> Sequence[Camera]:
            return self.camera_service.get_all()

        @self.router.get("/{ip}/stream")
        async def get_camera_stream_by_ip(request: Request, ip: str):
            """MJPEG stream from camera for live viewing"""
            camera = self.camera_service.get_by_ip(ip)

            async def generate():
                cmd = [
                    "ffmpeg",
                    "-rtsp_transport", "tcp",
                    "-i", f"rtsp://{camera.username}:{camera.password}@{camera.ip}:{camera.port}/{camera.path}",
                    "-r", "10",
                    "-s", "640x480",  # Reduced resolution for performance on streaming
                    "-f", "mjpeg",
                    "-q:v", "5",
                    "-"
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )

                try:
                    while True:
                        # Read JPEG frames
                        jpeg_start = b'\xff\xd8'
                        jpeg_end = b'\xff\xd9'

                        buffer = b''
                        while True:
                            chunk = await process.stdout.read(4096)
                            if not chunk:
                                break

                            buffer += chunk

                            # Look for complete JPEG frame
                            start_idx = buffer.find(jpeg_start)
                            if start_idx != -1:
                                end_idx = buffer.find(jpeg_end, start_idx)
                                if end_idx != -1:
                                    # Complete frame found
                                    frame = buffer[start_idx:end_idx + 2]
                                    buffer = buffer[end_idx + 2:]

                                    # Send frame as multipart
                                    yield (
                                            b'--frame\r\n'
                                            b'Content-Type: image/jpeg\r\n\r\n' +
                                            frame +
                                            b'\r\n'
                                    )

                                    # Check if client disconnected
                                    if await request.is_disconnected():
                                        break

                        if await request.is_disconnected():
                            break

                except Exception as e:
                    print(f"Streaming error for camera {ip}: {e}")
                finally:
                    process.terminate()
                    await process.wait()

            return StreamingResponse(
                generate(),
                media_type="multipart/x-mixed-replace; boundary=frame"
            )