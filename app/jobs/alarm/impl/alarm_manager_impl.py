from app.clients.alarm_events_client import AlarmEventsClient
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.detection.detection_manager import DetectionManager
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.recording import Recording, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.sensor.sensor_repository import SensorRepository
from app.services.recording.recording_service import RecordingService
from app.utils.delayed_execution import delay_execution
from app.utils.event_manager import event_manager


class AlarmManagerImpl(AlarmManager):
    def __init__(self,
                 alarm_events_client: AlarmEventsClient,
                 recording_service: RecordingService,
                 device_group_repository: DeviceGroupRepository,
                 camera_repository: CameraRepository,
                 sensor_repository: SensorRepository):
        self.alarm_events_client = alarm_events_client
        self.recording_service = recording_service
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.sensor_repository = sensor_repository
        self.detection_manager: DetectionManager | None = None
        self.alarm = False
        self.alarm_recording_duration = 120

    def set_detection_manager(self, detection_manager: DetectionManager):
        self.detection_manager = detection_manager

    def on_sensor_triggered(self, sensor_id: str):
        """Called when any sensor is triggered (goes HIGH)"""
        sensor = self.sensor_repository.find_by_id(sensor_id)
        group = self.device_group_repository.find_listening_device_group()

        # If not already in alarm and sensor goes HIGH, trigger alarm immediately
        if not self.alarm and group and group.status == DeviceGroupStatus.LISTENING:
            self.alarm = True
            # Disable motion detection warnings immediately
            if self.detection_manager:
                self.detection_manager.on_group_leave_listening()

            try:
                self.alarm_events_client.notify_alarm_waiting(
                    started=True,
                    duration=group.wait_to_fire_alarm
                )
            except Exception as e:
                print(f"Warning: failed to start waiting audio for sensor trigger: {e}")

            delay_execution(
                func=self.trigger_alarm,
                args=(sensor.name, group.id),
                delay_seconds=group.wait_to_fire_alarm)

    def trigger_alarm(self, sensor_name: str, group_id: int):
        """Trigger the alarm after the delay"""
        # Find listening group and set it to alarm
        group = self.device_group_repository.find_device_group_by_id(group_id)

        # Check if still listening
        if group.status != DeviceGroupStatus.LISTENING:
            # Cleanup: stop waiting audio and reset alarm flag
            try:
                self.alarm_events_client.notify_alarm_waiting(started=False)
            except Exception:
                pass
            self.alarm = False
            return

        group.status = DeviceGroupStatus.ALARM
        self.device_group_repository.update_device_group(group)

        # Publish status change event
        event_manager.publish_device_group_event_sync(group_id, DeviceGroupStatus.ALARM.value)

        self.alarm_events_client.notify_alarm_waiting(started=False)

        # After the configured alarm duration, stop audio and recordings
        delay_execution(
            func=self.stop_alarm,
            delay_seconds=self.alarm_recording_duration)

        self.alarm_events_client.notify_sensor_alarm(sensor_name, duration=self.alarm_recording_duration)

        # Start recording for cameras that are not always recording
        for camera in self.camera_repository.find_all():
            if not camera.always_recording:
                self.recording_service.create_and_start_recording(
                    Recording.from_dto(RecordingInputDto(camera_ip=camera.ip, always_recording=False)))

    def stop_alarm(self):
        """Stop the alarm"""
        if self.alarm:
            self.alarm_events_client.notify_alarm_stopped()

            for camera in self.camera_repository.find_all():
                if not camera.always_recording:
                    self.recording_service.stop_by_camera_ip(camera.ip)
            self.alarm = False