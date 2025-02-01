from abc import abstractmethod

from app.models.enums.pir_status import PirStatus
from app.models.pir import Pir


class PirsListener:
    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def add_pir(self, pir: Pir):
        pass

    @abstractmethod
    def update_pir(self, pir: Pir):
        pass

    @abstractmethod
    def remove_pir(self, pir: Pir):
        pass

    @abstractmethod
    def get_status_by_pir(self, pir: Pir) -> PirStatus:
        pass
