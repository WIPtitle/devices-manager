from typing import Sequence

from fastapi import Request
from pydantic import BaseModel

from app.clients.auth_client import AuthClient
from app.config.bindings import inject
from app.exceptions.authorization_exception import AuthorizationException
from app.models.system_config import GpioServer, Mp3Server
from app.routers.router_wrapper import RouterWrapper
from app.services.system_config.system_config_service import SystemConfigService


class ConfigUpdateRequest(BaseModel):
    value: str


class SystemConfigRouter(RouterWrapper):
    @inject
    def __init__(self, system_config_service: SystemConfigService, auth_client: AuthClient):
        super().__init__(prefix="/config")
        self.system_config_service = system_config_service
        self.auth_client = auth_client

    def _define_routes(self):
        @self.router.get("/")
        def get_all_config() -> dict:
            return self.system_config_service.get_all_config()

        @self.router.put("/{key}")
        async def update_config(request: Request, key: str, body: ConfigUpdateRequest):
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            self.system_config_service.update_config(key, body.value)
            return {"key": key, "value": body.value}

        # --- GPIO Servers ---

        @self.router.get("/gpio-servers")
        def get_gpio_servers() -> Sequence[GpioServer]:
            return self.system_config_service.get_all_gpio_servers()

        @self.router.post("/gpio-servers")
        async def create_gpio_server(request: Request, server: GpioServer):
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.system_config_service.create_gpio_server(server)

        @self.router.delete("/gpio-servers/{server_id}")
        async def delete_gpio_server(request: Request, server_id: int):
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            self.system_config_service.delete_gpio_server(server_id)
            return {"deleted": True}

        # --- MP3 Servers ---

        @self.router.get("/mp3-servers")
        def get_mp3_servers() -> Sequence[Mp3Server]:
            return self.system_config_service.get_all_mp3_servers()

        @self.router.post("/mp3-servers")
        async def create_mp3_server(request: Request, server: Mp3Server):
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.system_config_service.create_mp3_server(server)

        @self.router.put("/mp3-servers/{server_id}")
        async def update_mp3_server(request: Request, server_id: int, server: Mp3Server):
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            server.id = server_id
            return self.system_config_service.update_mp3_server(server)

        @self.router.delete("/mp3-servers/{server_id}")
        async def delete_mp3_server(request: Request, server_id: int):
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            self.system_config_service.delete_mp3_server(server_id)
            return {"deleted": True}
