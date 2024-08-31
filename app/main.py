from typing import List

from fastapi import FastAPI

from app.routers.impl.gpio_config_router import GpioConfigRouter
from app.routers.router_wrapper import RouterWrapper


routers: List[RouterWrapper] = [
    GpioConfigRouter()
]

app = FastAPI()
for router in routers:
    app.include_router(router.get_fastapi_router())
