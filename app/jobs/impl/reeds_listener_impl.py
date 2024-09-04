import threading
import time
from typing import Dict

import RPi.GPIO as GPIO

from app.exceptions.reeds_listener_exception import ReedsListenerException
from app.jobs.reeds_listener import ReedsListener
from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed


def read_current_status_by_reed(reed: Reed) -> ReedStatus:
    value_when_closed = reed.default_value_when_closed.to_library_value()
    pull = GPIO.PUD_DOWN if value_when_closed == GPIO.HIGH else GPIO.PUD_UP
    GPIO.setup(reed.gpio_pin_number, GPIO.IN, pull_up_down=pull)
    current_value = GPIO.input(reed.gpio_pin_number)

    if (value_when_closed == GPIO.HIGH and current_value == GPIO.HIGH) or \
            (value_when_closed == GPIO.LOW and current_value == GPIO.LOW):
        return ReedStatus.CLOSED
    else:
        return ReedStatus.OPEN


class ReedListenerImpl(ReedsListener):
    def __init__(self):
        self.reeds_status: Dict[Reed, ReedStatus] = {}
        self.running = True
        self.thread = threading.Thread(target=self.monitor_pins)
        self.thread.start()
        GPIO.setmode(GPIO.BCM)


    def stop(self):
        self.running = False
        self.thread.join()
        GPIO.cleanup()


    def add_reed(self, reed: Reed):
        if reed not in self.reeds_status:
            self.reeds_status[reed] = read_current_status_by_reed(reed)
        else:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} already being monitored")


    def remove_reed(self, reed: Reed):
        if reed in self.reeds_status:
            GPIO.cleanup(reed.gpio_pin_number)
            del self.reeds_status[reed]
        else:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} not being monitored")


    def get_status_by_reed(self, reed: Reed) -> ReedStatus:
        if reed in self.reeds_status:
            status = self.reeds_status[reed]
            return ReedStatus(reed.gpio_pin_number, status)
        else:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} not being monitored")


    def monitor_pins(self):
        while self.running:
            for reed in self.reeds_status.keys():
                current_status = read_current_status_by_reed(reed)
                if current_status != self.reeds_status[reed]:
                    self.reeds_status[reed] = current_status
                    print(f"Changed status on pin {reed.gpio_pin_number}")
                    print(f"Status: {current_status}")
            time.sleep(5)
