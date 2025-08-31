from typing import Sequence, List
from fastapi.responses import StreamingResponse

from app.config.bindings import inject
from app.models.sensor import Sensor, SensorInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.sensor.sensor_service import SensorService


class SensorRouter(RouterWrapper):
    @inject
    def __init__(self, sensor_service: SensorService):
        super().__init__(prefix=f"/sensor")
        self.sensor_service = sensor_service

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
        def create_sensor(sensor: SensorInputDto) -> Sensor:
            return self.sensor_service.create(Sensor.from_dto(sensor))

        @self.router.put("/{sensor_id}")
        def update_sensor(sensor_id: str, sensor: Sensor) -> Sensor:
            return self.sensor_service.update(sensor_id, sensor)

        @self.router.delete("/{sensor_id}")
        def delete_sensor_by_id(sensor_id: str) -> Sensor:
            return self.sensor_service.delete_by_id(sensor_id)

        @self.router.get("/{sensor_id}/status")
        def get_sensor_status_by_id(sensor_id: str) -> dict:
            status = self.sensor_service.get_status_by_id(sensor_id)
            return {"status": "HIGH" if status == 1 else "LOW"}

        @self.router.get("/{sensor_id}/status/stream")
        def get_sensor_status_stream(sensor_id: str) -> StreamingResponse:
            return StreamingResponse(self.sensor_service.get_sensor_status_stream_by_id(sensor_id),
                                     media_type="text/event-stream")