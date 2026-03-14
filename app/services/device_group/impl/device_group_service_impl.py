import asyncio
import threading
from typing import Sequence

from app.clients.alarm_events_client import AlarmEventsClient
from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.detection.detection_manager import DetectionManager
from app.jobs.detection.impl.notification_scheduler import NotificationScheduler
from app.models.camera import Camera
from app.models.device_group import DeviceGroup
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.sensor import Sensor
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.sensor.sensor_repository import SensorRepository
from app.services.device_group.device_group_service import DeviceGroupService
from app.utils.delayed_execution import delay_execution, CancellableExecution
from app.utils.event_manager import event_manager


class DeviceGroupServiceImpl(DeviceGroupService):
    def __init__(self,
                 device_group_repository: DeviceGroupRepository,
                 camera_repository: CameraRepository,
                 sensor_repository: SensorRepository,
                 alarm_manager: AlarmManager,
                 alarm_events_client: AlarmEventsClient,
                 detection_manager: DetectionManager,
                 notification_scheduler: NotificationScheduler):
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.sensor_repository = sensor_repository
        self.alarm_manager = alarm_manager
        self.alarm_events_client = alarm_events_client
        self.detection_manager = detection_manager
        self.notification_scheduler = notification_scheduler
        self._pending_start_handles: dict[int, CancellableExecution] = {}

        # Publish initial state for all existing groups and recover detection
        for group in self.device_group_repository.find_all_devices_groups():
            # If restarted during WAITING_TO_START, promote to LISTENING (wait period has surely passed)
            if group.status == DeviceGroupStatus.WAITING_TO_START_LISTENING:
                print(f"Startup recovery: promoting group {group.name} from WAITING_TO_START_LISTENING to LISTENING")
                group.status = DeviceGroupStatus.LISTENING
                self.device_group_repository.update_device_group(group)
                sensors = self.device_group_repository.find_device_group_sensors_by_id(group.id)
                self.sensor_repository.update_listening_batch(sensors, True)

            event_manager.publish_device_group_event_sync(group.id, group.status.value)
            if group.status in (DeviceGroupStatus.LISTENING, DeviceGroupStatus.ALARM):
                group_cameras = self.device_group_repository.find_device_group_cameras_by_id(group.id)
                camera_ips = [c.ip for c in group_cameras]
                if camera_ips:
                    print(f"Startup recovery: restoring motion detection for group {group.name} ({len(camera_ips)} camera(s))")
                    self.detection_manager.on_group_start_listening(group.id, camera_ips)
                # If in ALARM state, detection workers are running but warnings must be disabled
                if group.status == DeviceGroupStatus.ALARM:
                    self.detection_manager.on_group_leave_listening()

    @staticmethod
    def _audio_fire_and_forget(fn, **kwargs):
        def _call():
            try:
                fn(**kwargs)
            except Exception as e:
                print(f"Warning: audio call failed: {e}")
        threading.Thread(target=_call, daemon=True).start()

    def create_device_group(self, device_group: DeviceGroup) -> DeviceGroup:
        if device_group.wait_to_fire_alarm > 120:
            raise BadRequestException("wait_to_fire_alarm can't be greater than 120 seconds")
        if device_group.wait_to_start_alarm > 120:
            raise BadRequestException("wait_to_start_alarm can't be greater than 120 seconds")
        group = self.device_group_repository.create_device_group(device_group)
        # Publish initial state for new group
        event_manager.publish_device_group_event_sync(group.id, group.status.value)
        return group

    def delete_device_group(self, group_id: int):
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't delete while not idle")
        return self.device_group_repository.delete_device_group(group_id)

    def update_device_group(self, group_id: int, group: DeviceGroup) -> DeviceGroup:
        if group_id != group.id:
            raise BadRequestException("Can't update group id")
        if group.status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't set listening value here")
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't update while not idle")

        updated_group = self.device_group_repository.update_device_group(group)
        # Publish status change event if status changed
        event_manager.publish_device_group_event_sync(group_id, updated_group.status.value)
        return updated_group

    def get_device_group_by_id(self, group_id: int) -> DeviceGroup:
        return self.device_group_repository.find_device_group_by_id(group_id)

    async def get_device_group_status_stream_by_id(self, group_id: int):
        """Stream device group status updates using events instead of polling"""
        # First, send the current status
        current_group = self.device_group_repository.find_device_group_by_id(group_id)
        yield f"data: {current_group.status.value}\n\n"

        # Subscribe to events for this device group
        queue = await event_manager.subscribe_to_device_group(group_id)

        try:
            while True:
                try:
                    # Wait for events with a timeout to handle client disconnections
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {event.data}\n\n"
                except asyncio.TimeoutError:
                    # Send a keep-alive comment to prevent connection timeout
                    yield f": keep-alive\n\n"
        finally:
            # Clean up subscription when client disconnects
            await event_manager.unsubscribe_device_group(group_id, queue)
            print(f"Client disconnected from device group {group_id} stream")

    def get_device_group_sensors_by_id(self, group_id: int) -> Sequence[Sensor]:
        return self.device_group_repository.find_device_group_sensors_by_id(group_id)

    def update_device_group_sensors_by_id(self, group_id: int, sensor_ids: Sequence[str]) -> Sequence[Sensor]:
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't update while not idle")
        return self.device_group_repository.update_device_group_sensors_by_id(group_id, sensor_ids)

    def get_device_group_cameras_by_id(self, group_id: int) -> Sequence[Camera]:
        return self.device_group_repository.find_device_group_cameras_by_id(group_id)

    def update_device_group_cameras_by_id(self, group_id: int, camera_ips: Sequence[str]) -> Sequence[Camera]:
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't update while not idle")
        return self.device_group_repository.update_device_group_cameras_by_id(group_id, camera_ips)

    def get_all_device_groups(self) -> Sequence[DeviceGroup]:
        return self.device_group_repository.find_all_devices_groups()

    def start_listening(self, group_id: int) -> DeviceGroup:
        group = self.get_device_group_by_id(group_id)
        if group.status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Group is not idle")

        # Only permit start listening if no other group is listening
        if not self.device_group_repository.are_all_groups_idle():
            raise BadRequestException("Not all groups are idle, can't start listening")

        # 1. Persist to DB first — this is the operation that can fail
        group.status = DeviceGroupStatus.WAITING_TO_START_LISTENING
        updated_group = self.device_group_repository.update_device_group(group)

        # 2. Publish status change event
        event_manager.publish_device_group_event_sync(group_id, DeviceGroupStatus.WAITING_TO_START_LISTENING.value)

        # 3. Schedule transition to LISTENING
        handle = delay_execution(func=self.do_start_listening, args=(group_id,), delay_seconds=group.wait_to_start_alarm)
        self._pending_start_handles[group_id] = handle

        # 4. Start audio (fire-and-forget)
        self._audio_fire_and_forget(
            self.alarm_events_client.notify_alarm_waiting,
            started=True, duration=group.wait_to_start_alarm + 5
        )

        return updated_group

    def stop_listening(self, group_id: int) -> DeviceGroup:
        group = self.get_device_group_by_id(group_id)
        allowed = {DeviceGroupStatus.LISTENING, DeviceGroupStatus.ALARM, DeviceGroupStatus.WAITING_TO_START_LISTENING}
        if group.status not in allowed:
            raise BadRequestException("Group is not listening, in alarm, or waiting to start")

        # Cancel pending start if still waiting
        pending = self._pending_start_handles.pop(group_id, None)
        if pending:
            pending.cancel()

        self.do_stop_listening(group_id)
        return self.get_device_group_by_id(group_id)

    def do_start_listening(self, group_id: int):
        self._pending_start_handles.pop(group_id, None)
        group = self.device_group_repository.find_device_group_by_id(group_id)

        # Guard: if the group was stopped while waiting, do nothing
        if group.status != DeviceGroupStatus.WAITING_TO_START_LISTENING:
            return

        group.status = DeviceGroupStatus.LISTENING
        self.device_group_repository.update_device_group(group)

        # Publish status change event
        event_manager.publish_device_group_event_sync(group_id, DeviceGroupStatus.LISTENING.value)

        sensors = self.get_device_group_sensors_by_id(group_id)
        self.sensor_repository.update_listening_batch(sensors, True)

        self._audio_fire_and_forget(self.alarm_events_client.notify_alarm_waiting, started=False)

        # Start motion detection only on cameras assigned to this group
        group_cameras = self.device_group_repository.find_device_group_cameras_by_id(group_id)
        camera_ips = [c.ip for c in group_cameras]
        self.detection_manager.on_group_start_listening(group_id, camera_ips)

    def do_stop_listening(self, group_id: int):
        sensors = self.get_device_group_sensors_by_id(group_id)
        self.sensor_repository.update_listening_batch(sensors, False)

        self.alarm_manager.stop_alarm()

        # Stop all audio (warning, waiting, alarm) regardless of current state
        self._audio_fire_and_forget(self.alarm_events_client.notify_alarm_stopped)

        # Cancel pending notifications for this group (alarm stopped = normal re-entry)
        self.notification_scheduler.cancel_group(group_id)

        # Stop motion detection on all cameras
        self.detection_manager.on_all_groups_idle()

        group = self.device_group_repository.find_device_group_by_id(group_id)
        group.status = DeviceGroupStatus.IDLE
        self.device_group_repository.update_device_group(group)

        # Publish status change event
        event_manager.publish_device_group_event_sync(group_id, DeviceGroupStatus.IDLE.value)