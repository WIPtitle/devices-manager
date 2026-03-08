from abc import abstractmethod
from typing import Sequence


class DetectionManager:
    @abstractmethod
    def on_group_start_listening(self, camera_ips: Sequence[str]):
        pass

    @abstractmethod
    def on_group_leave_listening(self):
        """Called when group leaves LISTENING state (sensor triggered, alarm, etc).
        Disables warning emission but keeps workers alive."""
        pass

    @abstractmethod
    def on_all_groups_idle(self):
        pass

    @abstractmethod
    def is_warning_enabled(self) -> bool:
        """Returns True if workers should emit warnings (only in LISTENING state)."""
        pass
