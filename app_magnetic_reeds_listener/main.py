from typing import List

from fastapi import FastAPI

from app_magnetic_reeds_listener.config.handlers import get_exception_handlers
from app_magnetic_reeds_listener.routers.impl.gpio_config_router import GpioConfigRouter
from app_magnetic_reeds_listener.routers.router_wrapper import RouterWrapper


exception_handlers = get_exception_handlers()
routers: List[RouterWrapper] = [
    GpioConfigRouter()
]

app = FastAPI()

for exc, handler in exception_handlers:
    app.add_exception_handler(exc, handler)

for router in routers:
    app.include_router(router.get_fastapi_router())
