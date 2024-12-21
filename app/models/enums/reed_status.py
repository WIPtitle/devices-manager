from enum import Enum


class ReedStatus(str, Enum):
    CLOSED = "CLOSED",
    OPEN = "OPEN"


    def to_dict(self):
        return {
            "status": self.value,
        }