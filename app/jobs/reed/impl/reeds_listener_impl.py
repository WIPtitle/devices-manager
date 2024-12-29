import threading
import time
from typing import Dict, Tuple

try:
    import RPi.GPIO as GPIO
except:
    from app.models.mock.GpioMock import GpioMock as GPIO

from app.exceptions.reeds_listener_exception import ReedsListenerException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.reed.reeds_listener import ReedsListener
from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed
from app.repositories.reed.reed_repository import ReedRepository


def read_current_status(gpio_pin_number: int, vcc: bool, normally_closed: bool) -> ReedStatus:
    if vcc:
        pull = GPIO.PUD_DOWN if normally_closed else GPIO.PUD_UP
    else:
        pull = GPIO.PUD_UP if normally_closed else GPIO.PUD_DOWN

    GPIO.setup(gpio_pin_number, GPIO.IN, pull_up_down=pull)
    current_value = GPIO.input(gpio_pin_number)

    if (normally_closed and current_value == GPIO.HIGH) or (not normally_closed and current_value == GPIO.LOW):
        return ReedStatus.CLOSED
    else:
        return ReedStatus.OPEN


class ReedsListenerImpl(ReedsListener):
    def __init__(self, alarm_manager: AlarmManager, reed_repository: ReedRepository):
        self.alarm_manager = alarm_manager
        self.reed_repository = reed_repository
        self.reed_infos: Dict[int, Tuple[bool, bool, ReedStatus]] = {}
        self.running = True
        self.thread = threading.Thread(target=self.monitor_pins)
        self.thread.start()
        GPIO.setmode(GPIO.BCM)


    def stop(self):
        self.running = False
        self.thread.join()
        GPIO.cleanup()


    def add_reed(self, reed: Reed):
        if self.reed_infos.get(reed.gpio_pin_number) is None:
            self.reed_infos[reed.gpio_pin_number] = (
                reed.vcc,
                reed.normally_closed,
                read_current_status(reed.gpio_pin_number, reed.vcc, reed.normally_closed)
            )
        else:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} already being monitored")


    def update_reed(self, reed: Reed):
        if self.reed_infos.get(reed.gpio_pin_number) is None:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} not being monitored")
        else:
            self.reed_infos[reed.gpio_pin_number] = (
                reed.vcc,
                reed.normally_closed,
                read_current_status(reed.gpio_pin_number, reed.vcc, reed.normally_closed)
            )


    def remove_reed(self, reed: Reed):
        if self.reed_infos.get(reed.gpio_pin_number) is None:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} not being monitored")
        else:
            GPIO.cleanup(reed.gpio_pin_number)
            del self.reed_infos[reed.gpio_pin_number]


    def get_status_by_reed(self, reed: Reed) -> ReedStatus:
        if self.reed_infos.get(reed.gpio_pin_number) is None:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} not being monitored")
        else:
            return self.reed_infos.get(reed.gpio_pin_number)[2]


    def monitor_pins(self):
        while self.running:
            time.sleep(1) # check every second

            for pin in self.reed_infos.keys():
                current_status = read_current_status(pin, self.reed_infos.get(pin)[0], self.reed_infos.get(pin)[1])
                if current_status != self.reed_infos.get(pin)[2]:
                    self.reed_infos[pin] = (
                        self.reed_infos.get(pin)[0],
                        self.reed_infos.get(pin)[1],
                        current_status
                    )
                    print(f"Status has changed for reed on gpio {pin}: {current_status.value}")

                    if self.reed_repository.find_by_gpio_pin_number(pin).listening:
                        # Alarm manager should be interacted with only when alarm is on
                        updated_reed = self.reed_repository.find_by_gpio_pin_number(pin)
                        self.alarm_manager.on_reed_changed_status(updated_reed.gpio_pin_number, current_status)
