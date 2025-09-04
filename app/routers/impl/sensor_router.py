from typing import Sequence, List
from fastapi import Request
from fastapi.responses import StreamingResponse

from app.clients.auth_client import AuthClient
from app.config.bindings import inject
from app.exceptions.authorization_exception import AuthorizationException
from app.models.sensor import Sensor, SensorInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.sensor.sensor_service import SensorService


class SensorRouter(RouterWrapper):
    @inject
    def __init__(self, sensor_service: SensorService, auth_client: AuthClient):
        super().__init__(prefix=f"/sensor")
        self.sensor_service = sensor_service
        self.auth_client = auth_client

    def _define_routes(self):
        @self.router.get("/servers")
        def get_available_gpio_servers() -> List[str]:
            """Get list of all configured GPIO monitor server URLs"""
            return self.sensor_service.get_available_gpio_servers()

        @self.router.get("/")
        def get_all_sensors() -> Sequence[Sensor]:
            return self.sensor_service.get_all()

        # Basic CRUD - parameterized routes come after static ones
        @self.router.get("/{sensor_id}")
        def get_sensor_by_id(sensor_id: str) -> Sensor:
            return self.sensor_service.get_by_id(sensor_id)

        @self.router.post("/", operation_id="create_sensor_slash")
        @self.router.post("", operation_id="create_sensor_without_slash")
        async def create_sensor(request: Request, sensor: SensorInputDto) -> Sensor:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.sensor_service.create(Sensor.from_dto(sensor))

        @self.router.put("/{sensor_id}")
        async def update_sensor(request: Request, sensor_id: str, sensor: Sensor) -> Sensor:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.sensor_service.update(sensor_id, sensor)

        @self.router.delete("/{sensor_id}")
        async def delete_sensor_by_id(request: Request, sensor_id: str) -> Sensor:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "MODIFY_DEVICES" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.sensor_service.delete_by_id(sensor_id)

        @self.router.get("/{sensor_id}/status")
        def get_sensor_status_by_id(sensor_id: str) -> dict:
            status = self.sensor_service.get_status_by_id(sensor_id)
            return {"status": "HIGH" if status == 1 else "LOW"}

        @self.router.get("/{sensor_id}/status/stream")
        def get_sensor_status_stream(sensor_id: str) -> StreamingResponse:
            return StreamingResponse(self.sensor_service.get_sensor_status_stream_by_id(sensor_id),
                                     media_type="text/event-stream")