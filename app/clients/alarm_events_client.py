import httpx


class AlarmEventsClient:
    def __init__(self):
        self.local_audio_hostname = "local-audio-manager"
        self.notifications_hostname = "notifications-manager"
        self.timeout = 10.0

    def notify_sensor_alarm(self, sensor_name: str):
        """Notify both audio and notifications services about a sensor alarm."""
        self._notify_audio_sensor_alarm(sensor_name)
        self._notify_notifications_sensor_alarm(sensor_name)

    def notify_alarm_waiting(self, started: bool):
        """Notify audio service about alarm waiting state."""
        url = f"http://{self.local_audio_hostname}:8000/internal/alarm/waiting"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json={"started": started})
            response.raise_for_status()

    def notify_alarm_stopped(self):
        """Notify audio service that alarm has stopped."""
        url = f"http://{self.local_audio_hostname}:8000/internal/alarm/stopped"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url)
            response.raise_for_status()

    def _notify_audio_sensor_alarm(self, sensor_name: str):
        """Notify audio service about sensor alarm."""
        url = f"http://{self.local_audio_hostname}:8000/internal/alarm/sensor-alarm"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json={"sensor_name": sensor_name})
            response.raise_for_status()

    def _notify_notifications_sensor_alarm(self, sensor_name: str):
        """Notify notifications service about sensor alarm."""
        url = f"http://{self.notifications_hostname}:8000/internal/alarm/sensor-alarm"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json={"sensor_name": sensor_name})
            response.raise_for_status()

    def notify_motion_warning(self, camera_name: str, snapshot_jpeg: bytes | None = None):
        """Notify audio service (warning sound) and save notification with snapshot to DB."""
        # Audio warning
        audio_url = f"http://{self.local_audio_hostname}:8000/internal/alarm/motion-warning"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                client.post(audio_url, json={"camera_name": camera_name})
        except Exception as e:
            print(f"Warning: failed to notify audio for motion warning: {e}")

        # Save notification with snapshot to DB (no push)
        notif_url = f"http://{self.notifications_hostname}:8000/internal/alarm/motion-warning"
        try:
            files = {}
            if snapshot_jpeg:
                files["snapshot"] = ("snapshot.jpg", snapshot_jpeg, "image/jpeg")
            with httpx.Client(timeout=self.timeout) as client:
                client.post(notif_url, data={"camera_name": camera_name}, files=files)
        except Exception as e:
            print(f"Warning: failed to save motion warning notification: {e}")
