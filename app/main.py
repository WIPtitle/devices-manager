from fastapi import FastAPI

from app.config.bindings import Bindings
from app.routers.config import gpio_config_router

app = FastAPI()

bindings = Bindings()
bindings.init_resources()
app.container = bindings

app.include_router(gpio_config_router.router)