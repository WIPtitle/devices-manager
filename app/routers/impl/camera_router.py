from typing import Sequence

from fastapi.responses import StreamingResponse

from app.config.bindings import inject
from app.exceptions.bad_request_exception import BadRequestException
from app.models.camera import Camera
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
        def create_camera(camera: Camera) -> Camera:
            return self.camera_service.create(camera)


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
        async def get_camera_stream_by_ip(ip: str):
            camera = self.camera_service.get_by_ip(ip)
            if not camera.is_reachable():
                return BadRequestException("Camera is not reachable")
            return StreamingResponse(self.camera_service.stream(camera), media_type='video/mp2t')
