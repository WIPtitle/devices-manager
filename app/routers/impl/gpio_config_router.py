from app.config.bindings import inject
from app.models.gpio_config import GpioConfig
from app.routers.router_wrapper import RouterWrapper
from app.services.gpio_config.gpio_config_service import GpioConfigService


class GpioConfigRouter(RouterWrapper):

    @inject
    def __init__(self, gpio_config_service: GpioConfigService):
        super().__init__(prefix=f"/config/gpio")
        self.gpio_config_service = gpio_config_service


    def _define_routes(self):
        @self.router.get("/{gpio_config_id}")
        def read_gpio_config(gpio_config_id: int):
            return self.gpio_config_service.get_by_id(gpio_config_id)

        @self.router.post("/", operation_id="post_slash")
        @self.router.post("", operation_id="post_without_slash")
        def create_gpio_config(gpio_config: GpioConfig):
            return self.gpio_config_service.create(gpio_config)

        @self.router.put("/", operation_id="put_slash")
        @self.router.put("", operation_id="put_without_slash")
        def update_gpio_config(gpio_config: GpioConfig):
            return self.gpio_config_service.update(gpio_config)

        @self.router.delete("/{gpio_config_id}")
        def delete_gpio_config(gpio_config_id: int):
            return self.gpio_config_service.delete_by_id(gpio_config_id)
