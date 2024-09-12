from abc import ABC, abstractmethod
from typing import Sequence

from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed


class ReedService(ABC):
    @abstractmethod
    def get_by_pin(self, gpio_pin_number: int) -> Reed:
        pass

    @abstractmethod
    def create(self, reed: Reed) -> Reed:
        pass

    @abstractmethod
    def update(self, gpio_pin_number: int, reed: Reed) -> Reed:
        pass

    @abstractmethod
    def delete_by_pin(self, gpio_pin_number: int) -> Reed:
        pass

    @abstractmethod
    def get_all(self) -> Sequence[Reed]:
        pass

    @abstractmethod
    def get_status_by_pin(self, gpio_pin_number: int) -> ReedStatus:
        pass
