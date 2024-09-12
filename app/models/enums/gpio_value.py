from enum import Enum

import RPi.GPIO as GPIO


class GpioValue(str, Enum):
    HIGH = "HIGH",
    LOW = "LOW"


    def to_library_value(self) -> GPIO:
        if self == GpioValue.HIGH:
            return GPIO.HIGH
        else:
            return GPIO.LOW


    @classmethod
    def from_library_value(cls, value: GPIO):
        if value == GPIO.HIGH:
            return cls.HIGH
        elif value == GPIO.LOW:
            return cls.LOW