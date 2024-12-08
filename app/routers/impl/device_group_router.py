from typing import List

from fastapi import Query, Request

from app.clients.auth_client import AuthClient
from app.config.bindings import inject
from app.exceptions.authentication_exception import AuthenticationException
from app.models.device_group import DeviceGroup, DeviceGroupInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.device_group.device_group_service import DeviceGroupService


class DeviceGroupRouter(RouterWrapper):
    @inject
    def __init__(self, device_group_service: DeviceGroupService, auth_client: AuthClient):
        super().__init__(prefix=f"/device-group")
        self.device_group_service = device_group_service
        self.auth_client = auth_client


    def _define_routes(self):
        @self.router.post("/")
        def create_device_group(device_group_dto: DeviceGroupInputDto):
            device_group = DeviceGroup.from_dto(device_group_dto)
            return self.device_group_service.create_device_group(device_group)


        @self.router.get("/{group_id}")
        def get_device_group(group_id: int):
            return self.device_group_service.get_device_group_by_id(group_id)


        @self.router.delete("/{group_id}")
        def delete_device_group(group_id: int):
            return self.device_group_service.delete_device_group(group_id)


        @self.router.put("/{group_id}")
        def update_device_group(group_id: int, group: DeviceGroup):
            return self.device_group_service.update_device_group(group_id, group)


        @self.router.get("/{group_id}/devices")
        def get_devices_in_group(group_id: int):
            return self.device_group_service.get_device_list_by_id(group_id)


        @self.router.post("/{group_id}/start-listening")
        def start_listening(request: Request, group_id: int, pin: str, force_listening: bool = Query(...)):
            if not self.auth_client.check_pin(token=request.headers.get("Authorization"), pin=pin):
                raise AuthenticationException("Incorrect PIN")
            return self.device_group_service.start_listening(group_id, force_listening)


        @self.router.post("/{group_id}/stop-listening")
        def stop_listening(request: Request, group_id: int, pin: str):
            if not self.auth_client.check_pin(token=request.headers.get("Authorization"), pin=pin):
                raise AuthenticationException("Incorrect PIN")
            return self.device_group_service.stop_listening(group_id)