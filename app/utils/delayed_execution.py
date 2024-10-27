import sched
import time
import threading

def delay_execution(func, args=(), delay_seconds: int = 0):
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(delay_seconds, 1, func, argument=args)
    threading.Thread(target=scheduler.run).start()
