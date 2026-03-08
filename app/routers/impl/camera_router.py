import subprocess
from typing import Sequence

from fastapi import Request
from fastapi.responses import Response, StreamingResponse

from app.clients.auth_client import AuthClient
from app.config.bindings import inject
from app.exceptions.authorization_exception import AuthorizationException
from app.exceptions.bad_request_exception import BadRequestException
from app.models.camera import Camera, CameraInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.camera.camera_service import CameraService
from app.services.streaming.ffmpeg_streamer import FFmpegStreamManager

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

        @self.router.put("/{ip}")
        async def update_camera(request: Request, ip: str, camera: CameraInputDto) -> Camera:
            """Update camera - only name field can be modified"""
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")

            if camera.ip != ip:
                raise BadRequestException("IP in path does not match IP in request body")

            return self.camera_service.update(Camera.from_dto(camera))

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

        @self.router.post("/snapshot")
        async def get_camera_snapshot(request: Request, camera: CameraInputDto):
            """Grab a single JPEG frame from an RTSP camera (used for ROI drawing before creation)."""
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")

            cam = Camera.from_dto(camera)
            if cam.ip in ("localhost", "127.0.0.1"):
                cam.ip = "host.docker.internal"
            rtsp_url = cam.rtsp_url()

            try:
                cmd = [
                    "ffmpeg",
                    "-rtsp_transport", "tcp",
                    "-timeout", "5000000",
                    "-i", rtsp_url,
                    "-frames:v", "1",
                    "-f", "image2",
                    "-c:v", "mjpeg",
                    "-q:v", "5",
                    "pipe:1",
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                if result.returncode != 0 or not result.stdout:
                    raise BadRequestException("Could not capture frame from camera")
                return Response(content=result.stdout, media_type="image/jpeg")
            except subprocess.TimeoutExpired:
                raise BadRequestException("Camera snapshot timed out")
            except BadRequestException:
                raise
            except Exception as e:
                raise BadRequestException(f"Snapshot failed: {e}")

        @self.router.get("/{ip}/stream")
        async def get_camera_stream_by_ip(request: Request, ip: str):
            token = request.headers.get("Authorization")
            if token is None and request.query_params.get("auth_token") is not None:
                token = "Bearer " + request.query_params.get("auth_token")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "ACCESS_RECORDINGS" not in user.permissions:
                raise AuthorizationException("Not authorized")

            camera = self.camera_service.get_by_ip(ip)

            async def generate():
                try:
                    async for chunk in stream_manager.get_stream(camera):
                        yield chunk
                        if await request.is_disconnected():
                            break
                except Exception as e:
                    print(f"Stream error for camera {ip}: {e}")
                finally:
                    pass

            return StreamingResponse(
                generate(),
                media_type="video/mp4",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )