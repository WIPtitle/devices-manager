from enum import Enum


class DeviceType(str, Enum):
    MAGNETIC_REED = "MAGNETIC_REED",
    RTSP_CAMERA = "RTSP_CAMERA"
