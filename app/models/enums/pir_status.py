from enum import Enum


class PirStatus(str, Enum):
    MOVEMENT = "MOVEMENT",
    IDLE = "IDLE"


    def to_dict(self):
        return {
            "status": self.value,
        }