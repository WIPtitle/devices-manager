from abc import ABC, abstractmethod
from typing import Optional

from app.models.gpio_config import GpioConfig
from app.repositories.gpio_config.gpio_config_repository import GpioConfigRepository


class GpioConfigService(ABC):
    @abstractmethod
    def __init__(self, gpio_config_repository: GpioConfigRepository):
        pass

    @abstractmethod
    def get_by_id(self, gpio_config_id: int) -> Optional[GpioConfig]:
        pass

    @abstractmethod
    def create(self, gpio_config: GpioConfig) -> GpioConfig:
        pass

    @abstractmethod
    def update(self, gpio_config: GpioConfig) -> Optional[GpioConfig]:
        pass

    @abstractmethod
    def delete_by_id(self, gpio_config_id: int) -> GpioConfig:
        pass
