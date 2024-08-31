from fastapi import HTTPException

from app_magnetic_reeds_listener.config.bindings import inject
from app_magnetic_reeds_listener.routers.router_wrapper import RouterWrapper
from app_magnetic_reeds_listener.services.gpio_config.gpio_config_service import GpioConfigService
from app_magnetic_reeds_listener.models.gpio_config import GpioConfig


class GpioConfigRouter(RouterWrapper):

    @inject
    def __init__(self, gpio_config_service: GpioConfigService):
        super().__init__(prefix=f"/config/gpio")
        self.gpio_config_service = gpio_config_service


    def _define_routes(self):
        @self.router.get("/{gpio_config_id}")
        def read_gpio_config(gpio_config_id: int):
            gpio_config = self.gpio_config_service.get_by_id(gpio_config_id)
            if gpio_config is None:
                raise HTTPException(status_code=404, detail="GpioConfig not found")
            return gpio_config

        @self.router.post("/")
        def create_gpio_config(gpio_config: GpioConfig):
            gpio_config = self.gpio_config_service.create(gpio_config)
            return gpio_config

        @self.router.put("/")
        def update_gpio_config(gpio_config: GpioConfig):
            gpio_config = self.gpio_config_service.update(gpio_config)
            if gpio_config is None:
                raise HTTPException(status_code=404, detail="GpioConfig not found")
            return gpio_config

        @self.router.delete("/{gpio_config_id}")
        def delete_gpio_config(gpio_config_id: int):
            gpio_config = self.gpio_config_service.delete_by_id(gpio_config_id)
            if gpio_config is None:
                raise HTTPException(status_code=404, detail="GpioConfig not found")
            return gpio_config
