from typing import List, Optional

from sqlmodel import SQLModel, Field, Relationship

from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.pir import Pir
from app.models.reed import Reed


class DeviceGroupInputDto(SQLModel):
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int


class DeviceGroupReedLink(SQLModel, table=True):
    device_group_id: int = Field(foreign_key="devicegroup.id", primary_key=True)
    reed_gpio_pin_number: int = Field(foreign_key="reed.gpio_pin_number", primary_key=True)


class DeviceGroupPirLink(SQLModel, table=True):
    device_group_id: int = Field(foreign_key="devicegroup.id", primary_key=True)
    pir_gpio_pin_number: int = Field(foreign_key="pir.gpio_pin_number", primary_key=True)


class DeviceGroup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int
    status: DeviceGroupStatus
    reeds: List[Reed] = Relationship(link_model=DeviceGroupReedLink)
    pirs: List[Pir] = Relationship(link_model=DeviceGroupPirLink)

    @classmethod
    def from_dto(cls, dto: DeviceGroupInputDto):
        group = cls(
            id=None,
            name=dto.name,
            wait_to_start_alarm=dto.wait_to_start_alarm,
            wait_to_fire_alarm=dto.wait_to_fire_alarm,
            status=DeviceGroupStatus.IDLE,
            reeds=[],
            pirs=[],
        )
        return group