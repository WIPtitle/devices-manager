from abc import ABC, abstractmethod

from app.models.reed import Reed
from app.repositories.reed.reed_repository import ReedRepository


class ReedService(ABC):
    @abstractmethod
    def __init__(self, reed_repository: ReedRepository):
        pass

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
