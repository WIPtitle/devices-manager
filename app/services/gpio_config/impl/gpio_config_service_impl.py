from typing import Optional

from app.models.gpio_config import GpioConfig
from app.repositories.gpio_config.gpio_config_repository import GpioConfigRepository
from app.services.gpio_config.gpio_config_service import GpioConfigService


class GpioConfigServiceImpl(GpioConfigService):
    def __init__(self, gpio_config_repository: GpioConfigRepository):
        self.gpio_config_repository = gpio_config_repository

    def get_by_id(self, gpio_config_id: int) -> Optional[GpioConfig]:
        return self.gpio_config_repository.find_by_id(gpio_config_id)

    def create(self, gpio_config: GpioConfig) -> GpioConfig:
        return self.gpio_config_repository.create(gpio_config)

    def update(self, gpio_config: GpioConfig) -> Optional[GpioConfig]:
        return self.gpio_config_repository.update(gpio_config)

    def delete_by_id(self, gpio_config_id: int) -> GpioConfig:
        return self.gpio_config_repository.delete_by_id(gpio_config_id)
