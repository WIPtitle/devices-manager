from typing import List

from fastapi import FastAPI

from app.config.handlers import get_exception_handlers
from app.routers.impl.camera_router import CameraRouter
from app.routers.impl.disk_usage_router import DiskUsageRouter
from app.routers.impl.recording_router import RecordingRouter
from app.routers.router_wrapper import RouterWrapper
from app.utils.raspberry_check import is_raspberry

exception_handlers = get_exception_handlers()
routers: List[RouterWrapper] = [
    CameraRouter(),
    RecordingRouter(),
    DiskUsageRouter()
]

# Append routers that works only if host is a raspberry. There is a similar check in bindings since we do not
# want to import anything raspberry related on a non-raspberry host.
if is_raspberry():
    from app.routers.impl.reed_router import ReedRouter
    routers.append(ReedRouter())

app = FastAPI()

for exc, handler in exception_handlers:
    app.add_exception_handler(exc, handler)

for router in routers:
    app.include_router(router.get_fastapi_router())
