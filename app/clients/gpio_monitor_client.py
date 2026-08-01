import asyncio
import json
import logging
import threading
from dataclasses import dataclass
from typing import Dict, Callable, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PinState:
    pin: int
    state: int  # 0 = LOW, 1 = HIGH
    timestamp: int
    time: str
    confidence: Optional[str] = None


class GpioMonitorClient:
    def __init__(self, gpio_monitor_url: str):
        """
        Initialize GPIO Monitor client for a single server

        Args:
            gpio_monitor_url: URL of the GPIO Monitor server
        """
        self.gpio_monitor_url = gpio_monitor_url
        self.callbacks: Dict[int, Callable[[int, int], None]] = {}
        self.running = False
        self.thread = None
        self.loop = None
        self.monitored_pins = set()
        # Last known state per pin (pin -> 0/1), used to dedupe SSE "gpio_change"
        # events. On reconnect the server replays a burst of buffered events, so
        # we only fire callbacks on an actual transition, never on a replay of the
        # already-known state.
        self._pin_states: Dict[int, int] = {}
        self._pin_states_lock = threading.Lock()

    def start(self):
        """Start the SSE listener thread"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_event_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the SSE listener thread"""
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=5)

    def _run_event_loop(self):
        """Run the asyncio event loop in a separate thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._listen_to_events())
        except Exception as e:
            logger.error(f"Error in event loop: {e}")
        finally:
            self.loop.close()

    async def _listen_to_events(self):
        """Listen to SSE events from the GPIO Monitor"""
        while self.running:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                    async with client.stream('GET', f"{self.gpio_monitor_url}/events") as response:
                        response.raise_for_status()

                        async for line in response.aiter_lines():
                            if not self.running:
                                break

                            if line.startswith("event:"):
                                event_type = line.split(":", 1)[1].strip()
                            elif line.startswith("data:"):
                                data_str = line.split(":", 1)[1].strip()
                                try:
                                    data = json.loads(data_str)
                                    await self._handle_event(event_type, data)
                                except json.JSONDecodeError as e:
                                    logger.error(f"Failed to parse event data: {e}")

            except httpx.HTTPError as e:
                logger.error(f"HTTP error while listening to events: {e}")
                if self.running:
                    await asyncio.sleep(5)  # Retry after 5 seconds
            except Exception as e:
                logger.error(f"Unexpected error in event listener: {e}")
                if self.running:
                    await asyncio.sleep(5)

    async def _handle_event(self, event_type: str, data: dict):
        """Handle incoming SSE events"""
        if event_type == "gpio_change":
            pin = data.get("pin")
            state = data.get("state")

            if pin is not None and state is not None:
                # Dedupe: only treat this as a real transition if it differs from
                # the last known state for this pin. This filters out duplicate
                # events and reconnect replays (the server flushes a backlog of
                # buffered events on every reconnect), which would otherwise
                # re-fire the callback (and trigger the alarm) for a pin whose
                # state never actually changed.
                with self._pin_states_lock:
                    previous_state = self._pin_states.get(pin)
                    changed = previous_state != state
                    self._pin_states[pin] = state

                if changed:
                    # Check if pin is in callbacks (registered sensors)
                    if pin in self.callbacks:
                        callback = self.callbacks[pin]
                        # Run callback in a thread to avoid blocking
                        threading.Thread(target=callback, args=(pin, state)).start()

        elif event_type == "init":
            # Handle initial state. This is (re-)sent on every connect and
            # reconnect, so use it to silently resync our per-pin state cache
            # (no callbacks fired) rather than trusting the first post-reconnect
            # "gpio_change" event, which may just be a replay.
            pins = data.get("pins", {})
            monitored = data.get("monitored", [])

            with self._pin_states_lock:
                self._pin_states = {int(pin): pin_state for pin, pin_state in pins.items()}

            # Update monitored pins
            self.monitored_pins = set(monitored)

            logger.info(f"GPIO Monitor initialized with monitored pins: {monitored}")

    def register_callback(self, pin: int, callback: Callable[[int, int], None]):
        """Register a callback for pin state changes"""
        self.callbacks[pin] = callback
        # When registering a callback, also update monitored pins
        self._update_monitored_pins()

    def unregister_callback(self, pin: int):
        """Unregister a callback for a pin"""
        if pin in self.callbacks:
            del self.callbacks[pin]

    def _update_monitored_pins(self):
        """Update the list of monitored pins from the server"""
        try:
            response = httpx.get(f"{self.gpio_monitor_url}/api/pins")
            response.raise_for_status()
            data = response.json()
            monitored = data.get("monitored", [])
            self.monitored_pins = set(monitored)
            logger.debug(f"Updated monitored pins: {monitored}")
        except Exception as e:
            logger.error(f"Failed to update monitored pins: {e}")

    def is_pin_monitored(self, pin: int) -> bool:
        """Check if a pin is being monitored by the GPIO Monitor"""
        try:
            response = httpx.get(f"{self.gpio_monitor_url}/api/pins")
            response.raise_for_status()
            data = response.json()
            monitored = data.get("monitored", [])
            # Update our local cache while we're at it
            self.monitored_pins = set(monitored)
            return pin in monitored
        except Exception as e:
            logger.error(f"Failed to check if pin {pin} is monitored: {e}")
            return False

    def get_pin_state(self, pin: int) -> Optional[int]:
        """Get the current state of a pin"""
        try:
            response = httpx.get(f"{self.gpio_monitor_url}/api/pins/{pin}/state")
            response.raise_for_status()
            data = response.json()
            return data.get("state")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Pin {pin} not monitored")
            else:
                logger.error(f"Failed to get state for pin {pin}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get state for pin {pin}: {e}")
            raise

    def get_all_pins_info(self) -> dict:
        """Get information about all pins"""
        try:
            response = httpx.get(f"{self.gpio_monitor_url}/api/pins")
            response.raise_for_status()
            data = response.json()
            # Update monitored pins cache
            monitored = data.get("monitored", [])
            self.monitored_pins = set(monitored)
            return data
        except Exception as e:
            logger.error(f"Failed to get pins info: {e}")
            raise