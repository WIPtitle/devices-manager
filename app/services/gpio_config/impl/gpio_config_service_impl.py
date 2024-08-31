from typing import Optional

from app.exceptions.NotFoundException import NotFoundException
from app.models.gpio_config import GpioConfig
from app.repositories.gpio_config.gpio_config_repository import GpioConfigRepository
from app.services.gpio_config.gpio_config_service import GpioConfigService


class GpioConfigServiceImpl(GpioConfigService):
    def __init__(self, gpio_config_repository: GpioConfigRepository):
        self.gpio_config_repository = gpio_config_repository

    def get_by_id(self, gpio_config_id: int) -> GpioConfig:
        gpio_config: Optional[GpioConfig] = self.gpio_config_repository.find_by_id(gpio_config_id)
        if gpio_config is None:
            raise NotFoundException("Gpio config was not found")
        return gpio_config

    def create(self, gpio_config: GpioConfig) -> GpioConfig:
        return self.gpio_config_repository.create(gpio_config)

    def update(self, gpio_config: GpioConfig) -> GpioConfig:
        gpio_config = self.gpio_config_repository.update(gpio_config)
        if gpio_config is None:
            raise NotFoundException("Gpio config was not found")
        return gpio_config

    def delete_by_id(self, gpio_config_id: int) -> GpioConfig:
        return self.gpio_config_repository.delete_by_id(gpio_config_id)
