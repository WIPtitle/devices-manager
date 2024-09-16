import sched
import threading
import time

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.impl.devices_manager.alarm_stopped import AlarmStopped
from rabbitmq_sdk.event.impl.devices_manager.camera_alarm import CameraAlarm
from rabbitmq_sdk.event.impl.devices_manager.reed_alarm import ReedAlarm

from app.exceptions.bad_request_exception import BadRequestException
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


    # After two minutes, stop audio and recordings. This does NOT stop devices from listening so alarm could be triggered
    # again. Only user can stop devices from listening.
    def stop_alarm_automatically(self):
        scheduler = sched.scheduler(time.time, time.sleep)
        scheduler.enter(120, 1, self.stop_alarm)
        threading.Thread(target=scheduler.run).start()


    def on_camera_changed_status(self, camera_ip: str, camera_name: str, status: CameraStatus, blob: bytes | None):
        print(f"Changed status camera received: {status}, ALARM: {self.alarm}")
        if status == CameraStatus.MOVEMENT_DETECTED:
            # Record every movement even if alarm is already started
            try:
                self.recording_service.create(Recording.from_dto(RecordingInputDto(camera_ip=camera_ip)))
            except BadRequestException:
                print("Movement found but already recording with this camera")
            if not self.alarm:
                self.rabbitmq_client.publish(CameraAlarm(camera_name, blob, int(time.time())))
                self.alarm = True
                self.stop_alarm_automatically()
                print("ALARM STARTED")


    def on_reed_changed_status(self, reed_name: str, status: ReedStatus):
        print(f"Changed status reed received: {status}, ALARM: {self.alarm}")
        if status == ReedStatus.OPEN and self.alarm == False:
            self.rabbitmq_client.publish(ReedAlarm(reed_name, int(time.time())))
            self.alarm = True
            self.stop_alarm_automatically()
            print("ALARM STARTED")


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
        self.rabbitmq_client.publish(AlarmStopped(int(time.time())))
        self.alarm = False
        print("ALARM STOPPED")
