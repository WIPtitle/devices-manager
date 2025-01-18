from abc import abstractmethod

from app.models.enums.reed_status import ReedStatus


class AlarmManager:

    @abstractmethod
    def on_reed_changed_status(self, reed_pin: int, status: ReedStatus):
        pass

    @abstractmethod
    def stop_alarm(self):
        pass