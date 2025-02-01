from abc import abstractmethod

from app.models.enums.pir_status import PirStatus
from app.models.enums.reed_status import ReedStatus


class AlarmManager:

    @abstractmethod
    def on_reed_changed_status(self, reed_pin: int, status: ReedStatus):
        pass

    @abstractmethod
    def on_pir_changed_status(self, pir_pin: int, status: PirStatus):
        pass

    @abstractmethod
    def stop_alarm(self):
        pass