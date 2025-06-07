from enum import Enum


class RecordingType(str, Enum):
    ALARM = "ALARM",
    NORMAL = "NORMAL",