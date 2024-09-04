from abc import abstractmethod

from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed


class ReedsListener:
    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def add_reed(self, reed: Reed):
        pass

    @abstractmethod
    def remove_reed(self, reed: Reed):
        pass

    @abstractmethod
    def get_status_by_reed(self, reed: Reed) -> ReedStatus:
        pass
