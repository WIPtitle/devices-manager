from app.config.bindings import inject
from app.models.reed import Reed
from app.routers.router_wrapper import RouterWrapper
from app.services.reed.reed_service import ReedService


class ReedRouter(RouterWrapper):

    @inject
    def __init__(self, reed_service: ReedService):
        super().__init__(prefix=f"/config/gpio")
        self.reed_service = reed_service


    def _define_routes(self):
        @self.router.get("/{gpio_pin_number}")
        def get_reed_by_gpio_pin_number(gpio_pin_number: int):
            return self.reed_service.get_by_id(gpio_pin_number)

        @self.router.post("/", operation_id="post_slash")
        @self.router.post("", operation_id="post_without_slash")
        def create_reed(reed: Reed):
            return self.reed_service.create(reed)

        @self.router.put("/", operation_id="put_slash")
        @self.router.put("", operation_id="put_without_slash")
        def update_reed(reed: Reed):
            return self.reed_service.update(reed)

        @self.router.delete("/{gpio_pin_number}")
        def delete_reed_by_gpio_pin_number(gpio_pin_number: int):
            return self.reed_service.delete_by_id(gpio_pin_number)
