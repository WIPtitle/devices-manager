from typing import Sequence

from app.config.bindings import inject
from app.models.pir import Pir, PirInputDto
from app.routers.router_wrapper import RouterWrapper
from app.services.pir.pir_service import PirService


class PirRouter(RouterWrapper):
    @inject
    def __init__(self, pir_service: PirService):
        super().__init__(prefix=f"/pir")
        self.pir_service = pir_service


    def _define_routes(self):
        # Basic CRUD
        @self.router.get("/{gpio_pin_number}")
        def get_pir_by_gpio_pin_number(gpio_pin_number: int) -> Pir:
            return self.pir_service.get_by_pin(gpio_pin_number)


        @self.router.post("/", operation_id="create_slash")
        @self.router.post("", operation_id="create_without_slash")
        def create_pir(pir: PirInputDto) -> Pir:
            return self.pir_service.create(Pir.from_dto(pir))


        @self.router.put("/{gpio_pin_number}")
        def update_pir(gpio_pin_number: int, pir: Pir) -> Pir:
            return self.pir_service.update(gpio_pin_number, pir)


        @self.router.delete("/{gpio_pin_number}")
        def delete_pir_by_gpio_pin_number(gpio_pin_number: int) -> Pir:
            return self.pir_service.delete_by_pin(gpio_pin_number)


        # Other endpoints
        @self.router.get("/")
        def get_all_pirs() -> Sequence[Pir]:
            return self.pir_service.get_all()


        @self.router.get("/{gpio_pin_number}/status")
        def get_pir_status_by_gpio_pin_number(gpio_pin_number: int):
            return self.pir_service.get_status_by_pin(gpio_pin_number).to_dict()
