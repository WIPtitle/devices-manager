import threading


class CancellableExecution:
    def __init__(self):
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()


def delay_execution(func, args=(), delay_seconds: int = 0) -> CancellableExecution:
    handle = CancellableExecution()

    def _run():
        if delay_seconds > 0:
            if handle._cancelled.wait(timeout=delay_seconds):
                return
        if not handle.is_cancelled:
            func(*args)

    threading.Thread(target=_run, daemon=True).start()
    return handle
