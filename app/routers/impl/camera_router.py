import io
from typing import Sequence

from fastapi import Request
from fastapi.responses import StreamingResponse

from app.clients.auth_client import AuthClient
from app.config.bindings import inject
from app.exceptions.authorization_exception import AuthorizationException
from app.models.camera import Camera, CameraInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.camera.camera_service import CameraService
from app.services.streaming.ffmpeg_mjpeg_streamer import FFmpegStreamManager

stream_manager = FFmpegStreamManager()


class CameraRouter(RouterWrapper):
    @inject
    def __init__(self, camera_service: CameraService, auth_client: AuthClient):
        super().__init__(prefix=f"/camera")
        self.camera_service = camera_service
        self.auth_client = auth_client

    def _define_routes(self):
        @self.router.get("/{ip}")
        def get_camera_by_ip(ip: str) -> Camera:
            return self.camera_service.get_by_ip(ip)

        @self.router.post("/", operation_id="create_camera_slash")
        @self.router.post("", operation_id="create_camera_without_slash")
        async def create_camera(request: Request, camera: CameraInputDto) -> Camera:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.camera_service.create(Camera.from_dto(camera))

        @self.router.delete("/{ip}")
        async def delete_camera_by_ip(request: Request, ip: str) -> Camera:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            stream_manager.cleanup_stream(ip)
            return self.camera_service.delete_by_ip(ip)

        @self.router.get("/")
        def get_all_cameras() -> Sequence[Camera]:
            return self.camera_service.get_all()

        @self.router.get("/{ip}/stream")
        async def get_camera_stream_by_ip(request: Request, ip: str):
            token = request.headers.get("Authorization")
            if token is None and request.query_params.get("auth_token") is not None:
                token = "Bearer " + request.query_params.get("auth_token")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")

            camera = self.camera_service.get_by_ip(ip)

            async def generate():
                try:
                    async for frame in stream_manager.get_stream(camera):
                        yield frame
                        if await request.is_disconnected():
                            break
                except Exception as e:
                    print(f"Stream error for camera {ip}: {e}")
                finally:
                    pass

            return StreamingResponse(
                generate(),
                media_type="multipart/x-mixed-replace; boundary=frame",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )

        @self.router.get("/{ip}/snapshot")
        async def get_camera_snapshot(ip: str):
            camera = self.camera_service.get_by_ip(ip)

            async for frame in stream_manager.get_stream(camera):
                parts = frame.split(b'\r\n\r\n')
                if len(parts) > 1:
                    jpeg_data = parts[1].rstrip(b'\r\n')
                else:
                    jpeg_data = frame

                return StreamingResponse(
                    io.BytesIO(jpeg_data),
                    media_type="image/jpeg",
                    headers={
                        "Cache-Control": "no-cache",
                        "Content-Disposition": f"inline; filename=snapshot_{ip}.jpg"
                    }
                )

            return StreamingResponse(
                io.BytesIO(b''),
                status_code=503,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache",
                }
            )