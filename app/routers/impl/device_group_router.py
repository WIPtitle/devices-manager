from typing import Sequence

from app.clients.auth_client import AuthClient
from app.config.bindings import inject
from app.models.camera import Camera
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.reed import Reed
from app.models.device_group import DeviceGroup, DeviceGroupInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.device_group.device_group_service import DeviceGroupService
from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.authentication_exception import AuthenticationException

from fastapi import Response, Request, Query
from fastapi.responses import StreamingResponse


class DeviceGroupRouter(RouterWrapper):
    @inject
    def __init__(self, device_group_service: DeviceGroupService, auth_client: AuthClient):
        super().__init__(prefix=f"/device-group")
        self.device_group_service = device_group_service
        self.auth_client = auth_client


    def _define_routes(self):
        @self.router.get("/active-groups", response_class=Response)
        def get_if_group_active():
            device_groups = self.device_group_service.get_all_device_groups()
            if any(group.status != DeviceGroupStatus.IDLE for group in device_groups):
                return Response(status_code=204)
            else:
                raise BadRequestException("No active groups")


        @self.router.post("/")
        @self.router.post("", operation_id="post_device_group_without_slash")
        def create_device_group(device_group_dto: DeviceGroupInputDto) -> DeviceGroup:
            device_group = DeviceGroup.from_dto(device_group_dto)
            return self.device_group_service.create_device_group(device_group)


        @self.router.get("/{group_id}")
        def get_device_group(group_id: int) -> DeviceGroup:
            return self.device_group_service.get_device_group_by_id(group_id)


        @self.router.get("/{group_id}/status")
        def get_device_group_status(group_id: int) -> DeviceGroupStatus:
            return self.device_group_service.get_device_group_by_id(group_id).status


        @self.router.get("/{group_id}/status/stream")
        def get_device_group_status(group_id: int) -> StreamingResponse:
            return StreamingResponse(self.device_group_service.get_device_group_status_stream_by_id(group_id), media_type="text/event-stream")


        @self.router.get("/{group_id}/cameras")
        def get_device_group(group_id: int) -> Sequence[Camera]:
            return self.device_group_service.get_device_group_cameras_by_id(group_id)


        @self.router.get("/{group_id}/reeds")
        def get_device_group(group_id: int) -> Sequence[Reed]:
            return self.device_group_service.get_device_group_reeds_by_id(group_id)


        @self.router.put("/{group_id}/cameras")
        def update_device_group(group_id: int, camera_ips: Sequence[str]) -> Sequence[Camera]:
            return self.device_group_service.update_device_group_cameras_by_id(group_id, camera_ips)


        @self.router.put("/{group_id}/reeds")
        def update_device_group(group_id: int, reed_pins: Sequence[int]) -> Sequence[Reed]:
            return self.device_group_service.update_device_group_reeds_by_id(group_id, reed_pins)


        @self.router.delete("/{group_id}")
        def delete_device_group(group_id: int) -> DeviceGroup:
            return self.device_group_service.delete_device_group(group_id)


        @self.router.put("/{group_id}")
        def update_device_group(group_id: int, group: DeviceGroup) -> DeviceGroup:
            return self.device_group_service.update_device_group(group_id, group)


        @self.router.get("/")
        @self.router.get("", operation_id="get_all_device_groups_without_slash")
        def get_all_device_groups() -> Sequence[DeviceGroup]:
            return self.device_group_service.get_all_device_groups()


        @self.router.post("/{group_id}/start-listening")
        async def start_listening(request: Request, group_id: int):
            body = await request.json()
            pin = body.get("pin")
            if not await self.auth_client.check_pin(token=request.headers.get("Authorization"), pin=pin):
                raise AuthenticationException("Incorrect PIN")
            return self.device_group_service.start_listening(group_id)


        @self.router.post("/{group_id}/stop-listening")
        async def stop_listening(request: Request, group_id: int):
            body = await request.json()
            pin = body.get("pin")
            if not await self.auth_client.check_pin(token=request.headers.get("Authorization"), pin=pin):
                raise AuthenticationException("Incorrect PIN")
            return self.device_group_service.stop_listening(group_id)
