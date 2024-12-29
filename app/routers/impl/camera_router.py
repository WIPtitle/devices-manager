import time
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
        # Basic CRUD
        @self.router.get("/{ip}")
        def get_camera_by_ip(ip: str) -> Camera:
            return self.camera_service.get_by_ip(ip)


        @self.router.post("/", operation_id="create_camera_slash")
        @self.router.post("", operation_id="create_camera_without_slash")
        def create_camera(camera: CameraInputDto) -> Camera:
            return self.camera_service.create(Camera.from_dto(camera))


        @self.router.put("/{ip}")
        def update_camera(ip: str, camera: Camera) -> Camera:
            return self.camera_service.update(ip, camera)


        @self.router.delete("/{ip}")
        def delete_camera_by_ip(ip: str) -> Camera:
            return self.camera_service.delete_by_ip(ip)

        # Other endpoints
        @self.router.get("/")
        def get_all_cameras() -> Sequence[Camera]:
            return self.camera_service.get_all()


        @self.router.get("/{ip}/status")
        def get_camera_status_by_ip(ip: str):
            return self.camera_service.get_status_by_ip(ip).to_dict()


        @self.router.get("/{ip}/stream")
        async def get_camera_stream_by_ip(request: Request, ip: str):
            async def stream_frames():
                while True:
                    frame = self.camera_service.get_current_frame(ip)
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/webp\r\n\r\n" + frame + b"\r\n"
                    )
                    time.sleep(1)
                    if await request.is_disconnected():
                        break
            return StreamingResponse(stream_frames(), media_type="multipart/x-mixed-replace;boundary=frame")
