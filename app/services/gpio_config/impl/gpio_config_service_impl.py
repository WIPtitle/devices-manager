from app.models.gpio_config import GpioConfig
from app.repositories.gpio_config.gpio_config_repository import GpioConfigRepository
from app.services.gpio_config.gpio_config_service import GpioConfigService


class GpioConfigServiceImpl(GpioConfigService):
    def __init__(self, gpio_config_repository: GpioConfigRepository):
        self.gpio_config_repository = gpio_config_repository

    def get_gpio_config(self, gpio_config_id: int) -> GpioConfig:
        return self.gpio_config_repository.get_gpio_config(gpio_config_id)

    def create_gpio_config(self, gpio_config_id: int, value: int) -> GpioConfig:
        return self.gpio_config_repository.create_gpio_config(gpio_config_id, value)

    def update_gpio_config(self, gpio_config_id: int, value: int) -> GpioConfig:
        return self.gpio_config_repository.update_gpio_config(gpio_config_id, value)

    def delete_gpio_config(self, gpio_config_id: int) -> GpioConfig:
        return self.gpio_config_repository.delete_gpio_config(gpio_config_id)
