from abc import ABC, abstractmethod
from typing import Sequence

from app.models.enums.pir_status import PirStatus
from app.models.pir import Pir


class PirService(ABC):
    @abstractmethod
    def get_by_pin(self, gpio_pin_number: int) -> Pir:
        pass

    @abstractmethod
    def create(self, pir: Pir) -> Pir:
        pass

    @abstractmethod
    def update(self, gpio_pin_number: int, pir: Pir) -> Pir:
        pass

    @abstractmethod
    def delete_by_pin(self, gpio_pin_number: int) -> Pir:
        pass

    @abstractmethod
    def get_all(self) -> Sequence[Pir]:
        pass

    @abstractmethod
    def get_status_by_pin(self, gpio_pin_number: int) -> PirStatus:
        pass
