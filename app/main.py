import asyncio
from typing import List

from fastapi import FastAPI

from app.config.handlers import get_exception_handlers
from app.routers.impl.camera_router import CameraRouter
from app.routers.impl.device_group_router import DeviceGroupRouter
from app.routers.impl.disk_usage_router import DiskUsageRouter
from app.routers.impl.sensor_router import SensorRouter
from app.routers.impl.recording_router import RecordingRouter
from app.routers.impl.system_config_router import SystemConfigRouter
from app.routers.router_wrapper import RouterWrapper
from app.utils.event_manager import event_manager

exception_handlers = get_exception_handlers()
routers: List[RouterWrapper] = [
    CameraRouter(),
    SensorRouter(),
    RecordingRouter(),
    DiskUsageRouter(),
    DeviceGroupRouter(),
    SystemConfigRouter()
]

app = FastAPI()


@app.on_event("startup")
async def _register_event_loop():
    event_manager.set_main_loop(asyncio.get_running_loop())


for exc, handler in exception_handlers:
    app.add_exception_handler(exc, handler)

for router in routers:
    app.include_router(router.get_fastapi_router())