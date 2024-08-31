from fastapi import APIRouter, HTTPException

from app.config.bindings import inject
from app.routers.router_wrapper import RouterWrapper
from app.services.gpio_config.gpio_config_service import GpioConfigService
from app.models.gpio_config import GpioConfigDto


class GpioConfigRouter(RouterWrapper):

    @inject
    def __init__(self, gpio_config_service: GpioConfigService):
        super().__init__(prefix=f"/config/gpio")
        self.gpio_config_service = gpio_config_service


    def _define_routes(self):
        @self.router.get("/{gpio_config_id}")
        def read_gpio_config(gpio_config_id: int):
            gpio_config = self.gpio_config_service.get_gpio_config(gpio_config_id)
            if gpio_config is None:
                raise HTTPException(status_code=404, detail="GpioConfig not found")
            return gpio_config

        @self.router.post("/")
        def create_gpio_config(gpio_config_dto: GpioConfigDto):
            return self.gpio_config_service.create_gpio_config(gpio_config_id, value)

        @self.router.put("/{gpio_config_id}")
        def update_gpio_config(gpio_config_id: int, value: int):
            gpio_config = self.gpio_config_service.update_gpio_config(gpio_config_id, value)
            if gpio_config is None:
                raise HTTPException(status_code=404, detail="GpioConfig not found")
            return gpio_config

        @self.router.delete("/{gpio_config_id}")
        def delete_gpio_config(gpio_config_id: int):
            gpio_config = self.gpio_config_service.delete_gpio_config(gpio_config_id)
            if gpio_config is None:
                raise HTTPException(status_code=404, detail="GpioConfig not found")
            return gpio_config
