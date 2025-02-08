import time

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.base_event import BaseEvent
from rabbitmq_sdk.event.impl.devices_manager.alarm_stopped import AlarmStopped
from rabbitmq_sdk.event.impl.devices_manager.alarm_waiting import AlarmWaiting
from rabbitmq_sdk.event.impl.devices_manager.reed_alarm import ReedAlarm
from rabbitmq_sdk.event.impl.devices_manager.pir_alarm import PirAlarm

from app.jobs.alarm.alarm_manager import AlarmManager
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.enums.pir_status import PirStatus
from app.models.enums.reed_status import ReedStatus
from app.models.recording import Recording, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.pir.pir_repository import PirRepository
from app.repositories.reed.reed_repository import ReedRepository
from app.services.recording.recording_service import RecordingService
from app.utils.delayed_execution import delay_execution


# The logic here is that the devices' listeners perform a callback here every time the status changes and only if
# the device is actively listening to events (devices always listen to events but only perform callbacks if user
# started the alarm for those devices).
# Here I can emit events for other services (essentially, starting alarm only the first time an event that should start
# it happens, and shutting it down when user shuts it down).
class AlarmManagerImpl(AlarmManager):
    def __init__(self,
                 rabbitmq_client: RabbitMQClient,
                 recording_service: RecordingService,
                 device_group_repository: DeviceGroupRepository,
                 camera_repository: CameraRepository,
                 reed_repository: ReedRepository,
                 pir_repository: PirRepository):
        self.rabbitmq_client = rabbitmq_client
        self.recording_service = recording_service
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.reed_repository = reed_repository
        self.pir_repository = pir_repository
        self.alarm = False


    def on_reed_changed_status(self, reed_pin: int, status: ReedStatus):
        print(f"Changed status reed received: {status}, ALARM: {self.alarm}")
        reed = self.reed_repository.find_by_gpio_pin_number(reed_pin)
        group = self.device_group_repository.find_listening_device_group()

        # This filters the case where a reed is open on alarm start, because a changed status event will not be triggered
        # unless reed is closed after. If closed, nothing really happens, but if opened again another changed status
        # event will be triggered and this time it will start the alarm.
        if status == ReedStatus.OPEN and not self.alarm:
            self.alarm = True
            while not self.rabbitmq_client.publish(AlarmWaiting(True, int(time.time()))):
                time.sleep(1)
            delay_execution(
                func=self.trigger_alarm,
                args=(ReedAlarm(reed.name, int(time.time())), group.id),
                delay_seconds=group.wait_to_fire_alarm)


    def on_pir_changed_status(self, pir_pin: int, status: PirStatus):
        print(f"Changed status pir received: {status}, ALARM: {self.alarm}")
        pir = self.pir_repository.find_by_gpio_pin_number(pir_pin)
        group = self.device_group_repository.find_listening_device_group()

        if status == PirStatus.MOVEMENT and not self.alarm:
            self.alarm = True
            while not self.rabbitmq_client.publish(AlarmWaiting(True, int(time.time()))):
                time.sleep(1)
            delay_execution(
                func=self.trigger_alarm,
                args=(PirAlarm(pir.name, int(time.time())), group.id),
                delay_seconds=group.wait_to_fire_alarm)


    # OTHER ALARM FUNCTIONS

    def trigger_alarm(self, event: BaseEvent, group_id: int):
        while not self.rabbitmq_client.publish(AlarmWaiting(False, int(time.time()))):
            time.sleep(1)

        # After two minutes, stop audio and recordings. This does NOT stop devices from listening so alarm could be triggered
        # again. Only user can stop devices from listening.
        delay_execution(
            func=self.stop_alarm,
            delay_seconds=120)

        while not self.rabbitmq_client.publish(event):
            time.sleep(1)

        # Find listening group and set it to alarm
        group = self.device_group_repository.find_device_group_by_id(group_id)
        group.status = DeviceGroupStatus.ALARM
        self.device_group_repository.update_device_group(group)

        # Start recording for cameras that are not always recording to save videos of alarm event
        for camera in self.camera_repository.find_all():
            if not camera.always_recording:
                self.recording_service.create_and_start_recording(Recording.from_dto(RecordingInputDto(camera_ip=camera.ip, always_recording=False)))


    def stop_alarm(self):
        # Since this gets also called on stop listening, if alarm is not triggered there is no need to stop it
        if self.alarm:
            while not self.rabbitmq_client.publish(AlarmStopped(int(time.time()))):
                time.sleep(1)

            for camera in self.camera_repository.find_all():
                if not camera.always_recording:
                    self.recording_service.stop_by_camera_ip(camera.ip)
            self.alarm = False