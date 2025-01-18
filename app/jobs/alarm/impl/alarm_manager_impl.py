import time

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.base_event import BaseEvent
from rabbitmq_sdk.event.impl.devices_manager.alarm_stopped import AlarmStopped
from rabbitmq_sdk.event.impl.devices_manager.alarm_waiting import AlarmWaiting
from rabbitmq_sdk.event.impl.devices_manager.camera_alarm import CameraAlarm
from rabbitmq_sdk.event.impl.devices_manager.reed_alarm import ReedAlarm

from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.models.enums.camera_status import CameraStatus
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.enums.reed_status import ReedStatus
from app.models.recording import Recording, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
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
                 device_group_repository: DeviceGroupRepository,
                 camera_repository: CameraRepository,
                 reed_repository: ReedRepository,
                 recording_service: RecordingService):
        self.rabbitmq_client = rabbitmq_client
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.reed_repository = reed_repository
        self.recording_service = recording_service
        self.alarm = False


    # CALLBACK FUNCTIONS FOR LISTENERS
    def on_camera_changed_status(self, camera_ip: str, status: CameraStatus, blob: bytes | None):
        print(f"Changed status camera received: {status}, ALARM: {self.alarm}")
        camera = self.camera_repository.find_by_ip(camera_ip)
        group = self.device_group_repository.find_listening_device_group()

        if status == CameraStatus.MOVEMENT_DETECTED:
            # Record every movement even if alarm is already started
            try:
                self.recording_service.create(Recording.from_dto(RecordingInputDto(camera_ip=camera_ip)))
            except BadRequestException:
                print("Movement found but already recording with this camera")
            if not self.alarm:
                self.alarm = True
                while not self.rabbitmq_client.publish(AlarmWaiting(True, int(time.time()))):
                    time.sleep(1)
                delay_execution(
                    func=self.trigger_alarm,
                    args=(CameraAlarm(camera.name, blob, int(time.time())), group.id),
                    delay_seconds=group.wait_to_fire_alarm)


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
        if group.status == DeviceGroupStatus.LISTENING:
            group.status = DeviceGroupStatus.ALARM
            self.device_group_repository.update_device_group(group)


    # This of course gets called even if alarm is not running, I chose to emit the alarm stopped event anyway
    # and to ignore it on services that don't need it.
    # Currently only audio manager needs it to stop audio if still running, if it is not running it's not a problem.
    # Stop alarm DOESN'T MEAN that devices are not listening, it just stops recording and audio: this can happen
    # if user manually deactivates alarm, but it can also happen after a certain amount of time because
    # we do not want audio and recordings to go on forever (still, it will trigger again if devices change status again).
    def stop_alarm(self):
        all_recs = self.recording_service.get_all()
        for rec in all_recs:
            if not rec.is_completed:
                self.recording_service.stop(rec.id)
        while not self.rabbitmq_client.publish(AlarmStopped(int(time.time()))):
            time.sleep(1)
        self.alarm = False