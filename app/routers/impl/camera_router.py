import asyncio
from typing import Sequence
from fastapi import Request
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
            """Direct streaming without temporary file"""
            camera = self.camera_service.get_by_ip(ip)

            cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", f"rtsp://{camera.username}:{camera.password}@{camera.ip}:{camera.port}/{camera.path}",
                "-c:v", "copy",
                "-an",
                "-f", "matroska",
                "-"
            ]

            async def generate():
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )

                try:
                    while True:
                        chunk = await process.stdout.read(65536)
                        if not chunk:
                            break
                        yield chunk

                        if await request.is_disconnected():
                            break
                finally:
                    process.terminate()
                    await process.wait()

            return StreamingResponse(
                generate(),
                media_type="video/x-matroska",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )