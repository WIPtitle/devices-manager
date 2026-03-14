import asyncio
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    SENSOR_STATE_CHANGED = "sensor_state_changed"
    DEVICE_GROUP_STATUS_CHANGED = "device_group_status_changed"


@dataclass
class Event:
    type: EventType
    entity_id: Any  # sensor_id (str) for sensors, group_id (int) for device groups
    data: Any  # The new state/status


class EventManager:
    """Singleton event manager for handling state change events"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # Dictionary of entity_id -> list of queues for subscribers
        self._sensor_subscribers: Dict[str, List[asyncio.Queue]] = {}  # Changed to str for sensor IDs
        self._device_group_subscribers: Dict[int, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._main_loop: asyncio.AbstractEventLoop | None = None

    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        self._main_loop = loop

    async def subscribe_to_sensor(self, sensor_id: str) -> asyncio.Queue:
        """Subscribe to sensor state changes"""
        async with self._lock:
            queue = asyncio.Queue()
            if sensor_id not in self._sensor_subscribers:
                self._sensor_subscribers[sensor_id] = []
            self._sensor_subscribers[sensor_id].append(queue)
            print(f"New subscription to sensor {sensor_id}")
            return queue

    async def subscribe_to_device_group(self, group_id: int) -> asyncio.Queue:
        """Subscribe to device group status changes"""
        async with self._lock:
            queue = asyncio.Queue()
            if group_id not in self._device_group_subscribers:
                self._device_group_subscribers[group_id] = []
            self._device_group_subscribers[group_id].append(queue)
            print(f"New subscription to device group {group_id}")
            return queue

    async def unsubscribe_sensor(self, sensor_id: str, queue: asyncio.Queue):
        """Unsubscribe from sensor events"""
        async with self._lock:
            if sensor_id in self._sensor_subscribers:
                try:
                    self._sensor_subscribers[sensor_id].remove(queue)
                    if not self._sensor_subscribers[sensor_id]:
                        del self._sensor_subscribers[sensor_id]
                    print(f"Unsubscribed from sensor {sensor_id}")
                except ValueError:
                    pass

    async def unsubscribe_device_group(self, group_id: int, queue: asyncio.Queue):
        """Unsubscribe from device group events"""
        async with self._lock:
            if group_id in self._device_group_subscribers:
                try:
                    self._device_group_subscribers[group_id].remove(queue)
                    if not self._device_group_subscribers[group_id]:
                        del self._device_group_subscribers[group_id]
                    print(f"Unsubscribed from device group {group_id}")
                except ValueError:
                    pass

    async def publish_sensor_event(self, sensor_id: str, state: int):
        """Publish a sensor state change event"""
        event = Event(
            type=EventType.SENSOR_STATE_CHANGED,
            entity_id=sensor_id,
            data=state
        )

        async with self._lock:
            if sensor_id in self._sensor_subscribers:
                # Send to all subscribers
                for queue in self._sensor_subscribers[sensor_id]:
                    try:
                        await queue.put(event)
                    except asyncio.QueueFull:
                        print(f"Queue full for sensor {sensor_id} subscriber")

    async def publish_device_group_event(self, group_id: int, status: str):
        """Publish a device group status change event"""
        event = Event(
            type=EventType.DEVICE_GROUP_STATUS_CHANGED,
            entity_id=group_id,
            data=status
        )

        async with self._lock:
            if group_id in self._device_group_subscribers:
                # Send to all subscribers
                for queue in self._device_group_subscribers[group_id]:
                    try:
                        await queue.put(event)
                    except asyncio.QueueFull:
                        print(f"Queue full for device group {group_id} subscriber")

    def _schedule_coroutine(self, coro):
        """Schedule a coroutine from any thread, delivering it to the main event loop."""
        try:
            asyncio.get_running_loop()
            # We're inside the event loop thread — just create a task
            asyncio.create_task(coro)
        except RuntimeError:
            # We're in a background thread — dispatch to the main loop
            if self._main_loop is not None and self._main_loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, self._main_loop)

    def publish_sensor_event_sync(self, sensor_id: str, state: int):
        """Synchronous wrapper for publishing sensor events from any thread."""
        self._schedule_coroutine(self.publish_sensor_event(sensor_id, state))

    def publish_device_group_event_sync(self, group_id: int, status: str):
        """Synchronous wrapper for publishing device group events from any thread."""
        self._schedule_coroutine(self.publish_device_group_event(group_id, status))


# Global instance
event_manager = EventManager()