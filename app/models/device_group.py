from typing import List, Optional

from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey

from app.models.camera import Camera
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.reed import Reed


class DeviceGroupInputDto(SQLModel):
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int


class DeviceGroupCameraLink(SQLModel, table=True):
    device_group_id: int = Field(foreign_key="devicegroup.id", primary_key=True)
    camera_ip: str = Field(foreign_key="camera.ip", primary_key=True)


class DeviceGroupReedLink(SQLModel, table=True):
    device_group_id: int = Field(foreign_key="devicegroup.id", primary_key=True)
    reed_gpio_pin_number: int = Field(foreign_key="reed.gpio_pin_number", primary_key=True)


class DeviceGroup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int
    status: DeviceGroupStatus
    cameras: List[Camera] = Relationship(link_model=DeviceGroupCameraLink)
    reeds: List[Reed] = Relationship(link_model=DeviceGroupReedLink)

    @classmethod
    def from_dto(cls, dto: DeviceGroupInputDto):
        group = cls(
            id=None,
            name=dto.name,
            wait_to_start_alarm=dto.wait_to_start_alarm,
            wait_to_fire_alarm=dto.wait_to_fire_alarm,
            status=DeviceGroupStatus.IDLE,
            cameras=[],
            reeds=[]
        )
        return group