from typing import Sequence

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
        # Basic CRUD
        @self.router.get("/{gpio_pin_number}")
        def get_sensor_by_gpio_pin_number(gpio_pin_number: int) -> Sensor:
            return self.sensor_service.get_by_pin(gpio_pin_number)

        @self.router.post("/", operation_id="create_sensor_slash")
        @self.router.post("", operation_id="create_sensor_without_slash")
        def create_sensor(sensor: SensorInputDto) -> Sensor:
            return self.sensor_service.create(Sensor.from_dto(sensor))

        @self.router.put("/{gpio_pin_number}")
        def update_sensor(gpio_pin_number: int, sensor: Sensor) -> Sensor:
            return self.sensor_service.update(gpio_pin_number, sensor)

        @self.router.delete("/{gpio_pin_number}")
        def delete_sensor_by_gpio_pin_number(gpio_pin_number: int) -> Sensor:
            return self.sensor_service.delete_by_pin(gpio_pin_number)

        # Other endpoints
        @self.router.get("/")
        def get_all_sensors() -> Sequence[Sensor]:
            return self.sensor_service.get_all()

        @self.router.get("/{gpio_pin_number}/status")
        def get_sensor_status_by_gpio_pin_number(gpio_pin_number: int) -> dict:
            status = self.sensor_service.get_status_by_pin(gpio_pin_number)
            return {"status": "HIGH" if status == 1 else "LOW"}