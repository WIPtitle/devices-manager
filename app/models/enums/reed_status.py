from enum import Enum


class ReedStatus(str, Enum):
    CLOSED = "CLOSED",
    OPEN = "OPEN"