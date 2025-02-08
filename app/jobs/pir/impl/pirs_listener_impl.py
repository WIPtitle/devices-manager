import threading
import time
from typing import Dict

try:
    import RPi.GPIO as GPIO
except:
    from app.models.mock.GpioMock import GpioMock as GPIO

from app.exceptions.pirs_listener_exception import PirsListenerException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.pir.pirs_listener import PirsListener
from app.models.enums.pir_status import PirStatus
from app.models.pir import Pir
from app.repositories.pir.pir_repository import PirRepository


def read_current_status(gpio_pin_number: int) -> PirStatus:
    GPIO.setup(gpio_pin_number, GPIO.IN)
    if GPIO.input(gpio_pin_number):
        return PirStatus.MOVEMENT
    else:
        return PirStatus.IDLE


class PirsListenerImpl(PirsListener):
    def __init__(self, alarm_manager: AlarmManager, pir_repository: PirRepository):
        self.alarm_manager = alarm_manager
        self.pir_repository = pir_repository
        self.pir_infos: Dict[int, PirStatus] = {}
        self.running = True
        self.thread = threading.Thread(target=self.monitor_pins)
        self.thread.start()
        GPIO.setmode(GPIO.BCM)


    def stop(self):
        self.running = False
        self.thread.join()
        GPIO.cleanup()


    def add_pir(self, pir: Pir):
        if self.pir_infos.get(pir.gpio_pin_number) is None:
            self.pir_infos[pir.gpio_pin_number] = read_current_status(pir.gpio_pin_number)
        else:
            raise PirsListenerException(f"Pir with pin {pir.gpio_pin_number} already being monitored")


    def update_pir(self, pir: Pir):
        if self.pir_infos.get(pir.gpio_pin_number) is None:
            raise PirsListenerException(f"Pir with pin {pir.gpio_pin_number} not being monitored")
        else:
            self.pir_infos[pir.gpio_pin_number] = read_current_status(pir.gpio_pin_number)


    def remove_pir(self, pir: Pir):
        if self.pir_infos.get(pir.gpio_pin_number) is None:
            raise PirsListenerException(f"Pir with pin {pir.gpio_pin_number} not being monitored")
        else:
            GPIO.cleanup(pir.gpio_pin_number)
            del self.pir_infos[pir.gpio_pin_number]


    def get_status_by_pir(self, pir: Pir) -> PirStatus:
        if self.pir_infos.get(pir.gpio_pin_number) is None:
            raise PirsListenerException(f"Pir with pin {pir.gpio_pin_number} not being monitored")
        else:
            return self.pir_infos.get(pir.gpio_pin_number)


    def monitor_pins(self):
        while self.running:
            time.sleep(0.5) # check every half second

            for pin in self.pir_infos.keys():
                current_status = read_current_status(pin)
                if current_status != self.pir_infos.get(pin):
                    self.pir_infos[pin] = current_status

                    if self.pir_repository.find_by_gpio_pin_number(pin).listening:
                        # Alarm manager should be interacted with only when alarm is on
                        updated_pir = self.pir_repository.find_by_gpio_pin_number(pin)
                        self.alarm_manager.on_pir_changed_status(updated_pir.gpio_pin_number, current_status)
