import threading
import time
from typing import Dict

import RPi.GPIO as GPIO
from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.impl.devices_manager.enums.reed_status import ReedStatus as RabbitReedStatus
from rabbitmq_sdk.event.impl.devices_manager.reed_changed_status import ReedChangedStatus

from app.exceptions.reeds_listener_exception import ReedsListenerException
from app.jobs.reed.reeds_listener import ReedsListener
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


class ReedsListenerImpl(ReedsListener):
    def __init__(self, rabbitmq_client: RabbitMQClient):
        self.rabbitmq_client = rabbitmq_client
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


    def update_reed(self, reed: Reed):
        for r in list(self.reeds_status.keys()):
            if r.gpio_pin_number == reed.gpio_pin_number:
                self.remove_reed(r)
                self.add_reed(reed)
                return
        raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} not being monitored")


    def remove_reed(self, reed: Reed):
        if reed in self.reeds_status:
            GPIO.cleanup(reed.gpio_pin_number)
            del self.reeds_status[reed]
        else:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} not being monitored")


    def get_status_by_reed(self, reed: Reed) -> ReedStatus:
        if reed in self.reeds_status:
            return self.reeds_status[reed]
        else:
            raise ReedsListenerException(f"Reed with pin {reed.gpio_pin_number} not being monitored")


    def monitor_pins(self):
        while self.running:
            for reed in self.reeds_status.keys():
                current_status = read_current_status_by_reed(reed)
                if current_status != self.reeds_status[reed]:
                    # Status has changed, publish event
                    self.rabbitmq_client.publish(
                        ReedChangedStatus(
                            reed.gpio_pin_number,
                            RabbitReedStatus.OPEN if current_status == ReedStatus.OPEN else RabbitReedStatus.CLOSED,
                            int(time.time())
                        )
                    )
                    self.reeds_status[reed] = current_status
                    print(f"Status has changed for reed on gpio {reed.gpio_pin_number}: {current_status.value}")
            time.sleep(1)