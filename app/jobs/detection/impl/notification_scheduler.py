import threading

from app.clients.alarm_events_client import AlarmEventsClient


class NotificationScheduler:
    """Schedules motion warning notifications with a configurable delay.
    If the alarm group is stopped before the delay expires, pending notifications are cancelled."""

    def __init__(self, alarm_events_client: AlarmEventsClient):
        self._alarm_events_client = alarm_events_client
        self._pending: dict[int, list[threading.Timer]] = {}  # group_id -> timers
        self._lock = threading.Lock()
        self.delay_seconds = 0

    def schedule(self, group_id: int, camera_name: str, snapshot_jpeg: bytes | None):
        delay = self.delay_seconds
        if delay <= 0:
            self._alarm_events_client.send_motion_notification(camera_name, snapshot_jpeg)
            return

        timer = threading.Timer(delay, self._fire, args=[group_id, camera_name, snapshot_jpeg])
        with self._lock:
            if group_id not in self._pending:
                self._pending[group_id] = []
            self._pending[group_id].append(timer)
        timer.start()
        print(f"[NotifScheduler] Scheduled notification for group {group_id}, camera {camera_name} (delay={delay}s)")

    def cancel_group(self, group_id: int):
        with self._lock:
            timers = self._pending.pop(group_id, [])
        count = 0
        for timer in timers:
            timer.cancel()
            count += 1
        if count > 0:
            print(f"[NotifScheduler] Cancelled {count} pending notification(s) for group {group_id}")

    def cancel_all(self):
        with self._lock:
            all_timers = []
            for timers in self._pending.values():
                all_timers.extend(timers)
            self._pending.clear()
        for timer in all_timers:
            timer.cancel()
        if all_timers:
            print(f"[NotifScheduler] Cancelled all {len(all_timers)} pending notification(s)")

    def _fire(self, group_id: int, camera_name: str, snapshot_jpeg: bytes | None):
        # Clean up this timer from pending list
        with self._lock:
            if group_id in self._pending:
                self._pending[group_id] = [t for t in self._pending[group_id] if t.is_alive()]
                if not self._pending[group_id]:
                    del self._pending[group_id]

        try:
            self._alarm_events_client.send_motion_notification(camera_name, snapshot_jpeg)
            print(f"[NotifScheduler] Sent delayed notification for group {group_id}, camera {camera_name}")
        except Exception as e:
            print(f"[NotifScheduler] Error sending delayed notification: {e}")
