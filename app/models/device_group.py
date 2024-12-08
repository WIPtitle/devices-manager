from typing import List, Union, Optional
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from app.models.camera import Camera
from app.models.reed import Reed
from app.models.enums.device_group_status import DeviceGroupStatus


class DeviceGroupInputDto(SQLModel):
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int
    devices: List[Union[Camera, Reed]]


class DeviceGroup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int
    status: DeviceGroupStatus
    devices: List[Union[Camera, Reed]] = Relationship(
        back_populates="group", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @classmethod
    def from_dto(cls, dto: DeviceGroupInputDto):
        group = cls(
            id=None,
            name=dto.name,
            wait_to_start_alarm=dto.wait_to_start_alarm,
            wait_to_fire_alarm=dto.wait_to_fire_alarm,
            status=DeviceGroupStatus.IDLE,
            devices=dto.devices
        )

        return group