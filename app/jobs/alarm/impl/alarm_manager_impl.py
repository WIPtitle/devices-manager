import time

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.impl.devices_manager.alarm_stopped import AlarmStopped
from rabbitmq_sdk.event.impl.devices_manager.camera_alarm import CameraAlarm
from rabbitmq_sdk.event.impl.devices_manager.reed_alarm import ReedAlarm

from app.jobs.alarm.alarm_manager import AlarmManager
from app.models.enums.camera_status import CameraStatus
from app.models.enums.reed_status import ReedStatus
from app.models.recording import Recording, RecordingInputDto
from app.services.recording.recording_service import RecordingService


# The logic here is that the devices' listeners perform a callback here every time the status changes and only if
# the device is actively listening to events (devices always listen to events but only perform callbacks if user
# started the alarm for those devices).
# Here I can emit events for other services (essentially, starting alarm only the first time an event that should start
# it happens, and shutting it down when user shuts it down).
class AlarmManagerImpl(AlarmManager):
    def __init__(self, rabbitmq_client: RabbitMQClient):
        self.rabbitmq_client = rabbitmq_client
        self.recording_service = None
        self.alarm = False


    def set_recording_service(self, recording_service: RecordingService):
        self.recording_service = recording_service


    def on_camera_changed_status(self, camera_ip: str, camera_name: str, status: CameraStatus, blob: bytes | None):
        if status == CameraStatus.MOVEMENT_DETECTED:
            # Record every movement even if alarm is already started
            self.recording_service.create(Recording.from_dto(RecordingInputDto(camera_ip=camera_ip)))
            if not self.alarm:
                self.rabbitmq_client.publish(CameraAlarm(camera_name, blob, int(time.time())))
                self.alarm = True
                print("ALARM STARTED")


    def on_reed_changed_status(self, reed_name: str, status: ReedStatus):
        if status == ReedStatus.OPEN and self.alarm == False:
            self.rabbitmq_client.publish(ReedAlarm(reed_name, int(time.time())))
            self.alarm = True
            print("ALARM STARTED")


    # This of course gets called even if alarm is not running, I chose to emit the alarm stopped event anyway
    # and to ignore it on services that don't need it.
    # Currently only audio manager needs it to stop audio if still running, if it is not running it's not a problem.
    def on_all_devices_stopped_listening(self):
        all_recs = self.recording_service.get_all()
        for rec in all_recs:
            if not rec.is_completed:
                self.recording_service.stop(rec.id)
        self.rabbitmq_client.publish(AlarmStopped(int(time.time())))
        self.alarm = False
        print("ALARM STOPPED")
