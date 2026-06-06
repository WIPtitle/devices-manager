import httpx

TIMEOUT = 20.0


class AlarmEventsClient:
    def __init__(self):
        self.local_audio_hostname = "local-audio-manager"
        self.notifications_hostname = "notifications-manager"
        # Reuse one keep-alive connection pool instead of opening a fresh TCP
        # connection (and DNS lookup) on every event. httpx.Client is thread-safe,
        # which matters because these notifications are fired from daemon threads.
        self._client = httpx.Client(timeout=TIMEOUT)

    def _audio_url(self, path: str) -> str:
        return f"http://{self.local_audio_hostname}:8000{path}"

    def _notif_url(self, path: str) -> str:
        return f"http://{self.notifications_hostname}:8000{path}"

    def notify_sensor_alarm(self, sensor_name: str, duration: int = None):
        """Notify both audio and notifications services about a sensor alarm."""
        self._notify_audio_sensor_alarm(sensor_name, duration=duration)
        self._notify_notifications_sensor_alarm(sensor_name)

    def notify_alarm_waiting(self, started: bool, duration: int = None):
        """Notify audio service about alarm waiting state."""
        body = {"started": started}
        if duration is not None:
            body["duration"] = duration
        response = self._client.post(self._audio_url("/internal/alarm/waiting"), json=body, timeout=TIMEOUT)
        response.raise_for_status()

    def notify_alarm_stopped(self):
        """Notify audio service that alarm has stopped."""
        response = self._client.post(self._audio_url("/internal/alarm/stopped"), timeout=TIMEOUT)
        response.raise_for_status()

    def _notify_audio_sensor_alarm(self, sensor_name: str, duration: int = None):
        """Notify audio service about sensor alarm."""
        body = {"sensor_name": sensor_name}
        if duration is not None:
            body["duration"] = duration
        response = self._client.post(self._audio_url("/internal/alarm/sensor-alarm"), json=body, timeout=TIMEOUT)
        response.raise_for_status()

    def _notify_notifications_sensor_alarm(self, sensor_name: str):
        """Notify notifications service about sensor alarm."""
        response = self._client.post(self._notif_url("/internal/alarm/sensor-alarm"), json={"sensor_name": sensor_name}, timeout=TIMEOUT)
        response.raise_for_status()

    def notify_motion_warning_audio(self, camera_name: str):
        """Notify audio service about motion warning (immediate sound)."""
        try:
            self._client.post(self._audio_url("/internal/alarm/motion-warning"), json={"camera_name": camera_name}, timeout=TIMEOUT)
        except Exception as e:
            print(f"Warning: failed to notify audio for motion warning: {e}")

    def send_motion_notification(self, camera_name: str, snapshot_jpeg: bytes | None = None):
        """Send motion warning notification to notifications-manager (DB + ntfy push)."""
        try:
            files = {}
            if snapshot_jpeg:
                files["snapshot"] = ("snapshot.jpg", snapshot_jpeg, "image/jpeg")
            self._client.post(self._notif_url("/internal/alarm/motion-warning"), data={"camera_name": camera_name}, files=files, timeout=TIMEOUT)
        except Exception as e:
            print(f"Warning: failed to save motion warning notification: {e}")
