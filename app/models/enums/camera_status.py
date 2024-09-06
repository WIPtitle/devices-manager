from enum import Enum


class CameraStatus(str, Enum):
    MOVEMENT_DETECTED = "MOVEMENT_DETECTED",
    IDLE = "IDLE",
    UNREACHABLE = "UNREACHABLE"


    def to_dict(self):
        return {
            "camera_status": self.value,
        }