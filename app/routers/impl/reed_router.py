from typing import Sequence

from app.config.bindings import inject
from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed
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
            return self.reed_service.get_by_id(gpio_pin_number)


        @self.router.post("/", operation_id="create_slash")
        @self.router.post("", operation_id="create_without_slash")
        def create_reed(reed: Reed) -> Reed:
            return self.reed_service.create(reed)


        @self.router.put("/{gpio_pin_number}")
        def update_reed(gpio_pin_number: int, reed: Reed) -> Reed:
            return self.reed_service.update(gpio_pin_number, reed)


        @self.router.delete("/{gpio_pin_number}")
        def delete_reed_by_gpio_pin_number(gpio_pin_number: int) -> Reed:
            return self.reed_service.delete_by_id(gpio_pin_number)

        # Other endpoints
        @self.router.get("/")
        def get_all_reeds() -> Sequence[Reed]:
            return self.reed_service.get_all()


        @self.router.get("/{gpio_pin_number}/status")
        def get_reed_status_by_gpio_pin_number(gpio_pin_number: int) -> ReedStatus:
            return self.reed_service.get_status_by_id(gpio_pin_number)

