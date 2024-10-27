from enum import Enum


class DeviceGroupStatus(str, Enum):
    LISTENING = "LISTENING",
    IDLE = "IDLE",
    ALARM = "ALARM",
    WAITING_TO_START_LISTENING = "WAITING_TO_START_LISTENING"