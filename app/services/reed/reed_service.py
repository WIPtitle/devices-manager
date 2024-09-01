from abc import ABC, abstractmethod

from app.models.reed import Reed


class ReedService(ABC):
    @abstractmethod
    def get_by_id(self, gpio_pin_number: int) -> Reed:
        pass

    @abstractmethod
    def create(self, reed: Reed) -> Reed:
        pass

    @abstractmethod
    def update(self, reed: Reed) -> Reed:
        pass

    @abstractmethod
    def delete_by_id(self, gpio_pin_number: int) -> Reed:
        pass
