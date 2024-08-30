from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from app.config.bindings import Bindings
from app.services.gpio_config.impl.gpio_config_service_impl import GpioConfigService

router = APIRouter(
    prefix=f"/config/gpio",
)

@inject
@router.get("/{gpio_config_id}")
def read_gpio_config(gpio_config_id: int, service: GpioConfigService = Depends(Provide[Bindings.gpio_config_service_interface])):
    gpio_config = service.get_gpio_config(gpio_config_id)
    if gpio_config is None:
        raise HTTPException(status_code=404, detail="GpioConfig not found")
    return gpio_config

@inject
@router.post("/")
def create_gpio_config(gpio_config_id: int, value: int, service: GpioConfigService = Depends(Provide[Bindings.gpio_config_service_interface])):
    return service.create_gpio_config(gpio_config_id, value)

@inject
@router.put("/{gpio_config_id}")
def update_gpio_config(gpio_config_id: int, value: int, service: GpioConfigService = Depends(Provide[Bindings.gpio_config_service_interface])):
    gpio_config = service.update_gpio_config(gpio_config_id, value)
    if gpio_config is None:
        raise HTTPException(status_code=404, detail="GpioConfig not found")
    return gpio_config

@inject
@router.delete("/{gpio_config_id}")
def delete_gpio_config(gpio_config_id: int, service: GpioConfigService = Depends(Provide[Bindings.gpio_config_service_interface])):
    gpio_config = service.delete_gpio_config(gpio_config_id)
    if gpio_config is None:
        raise HTTPException(status_code=404, detail="GpioConfig not found")
    return gpio_config