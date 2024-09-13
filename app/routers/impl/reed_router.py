from typing import Sequence

from app.config.bindings import inject
from app.models.reed import Reed, ReedInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.reed.reed_service import ReedService


class ReedRouter(RouterWrapper):
    @inject
    def __init__(self, reed_service: ReedService):
        super().__init__(prefix=f"/reed")
        self.reed_service = reed_service


    def _define_routes(self):
        # Basic CRUD
        @self.router.get("/{gpio_pin_number}")
        def get_reed_by_gpio_pin_number(gpio_pin_number: int) -> Reed:
            return self.reed_service.get_by_pin(gpio_pin_number)


        @self.router.get("/generic/{device_id}")
        def get_camera_by_ip(device_id: int) -> Reed:
            return self.reed_service.get_by_generic_device_id(device_id)


        @self.router.post("/", operation_id="create_slash")
        @self.router.post("", operation_id="create_without_slash")
        def create_reed(reed: ReedInputDto) -> Reed:
            return self.reed_service.create(Reed.from_dto(reed))


        @self.router.put("/{gpio_pin_number}")
        def update_reed(gpio_pin_number: int, reed: Reed) -> Reed:
            return self.reed_service.update(gpio_pin_number, reed)


        @self.router.delete("/{gpio_pin_number}")
        def delete_reed_by_gpio_pin_number(gpio_pin_number: int) -> Reed:
            return self.reed_service.delete_by_pin(gpio_pin_number)


        # Other endpoints
        @self.router.get("/")
        def get_all_reeds() -> Sequence[Reed]:
            return self.reed_service.get_all()


        @self.router.get("/{gpio_pin_number}/status")
        def get_reed_status_by_gpio_pin_number(gpio_pin_number: int):
            return self.reed_service.get_status_by_pin(gpio_pin_number).to_dict()
