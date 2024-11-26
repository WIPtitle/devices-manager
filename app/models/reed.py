from typing import Optional

from sqlmodel import SQLModel, Field, Relationship

from app.models.enums.gpio_value import GpioValue


class ReedInputDto(SQLModel):
    gpio_pin_number: int
    name: str
    default_value_when_closed: GpioValue


class Reed(SQLModel, table=True):
    gpio_pin_number: int = Field(primary_key=True)
    name: str
    default_value_when_closed: GpioValue
    listening: bool
    group_id: Optional[int] = Field(default=None, foreign_key="devicegroup.id")
    group: Optional["DeviceGroup"] = Relationship(back_populates="reeds")

    @classmethod
    def from_dto(cls, dto: ReedInputDto):
        return cls(
            gpio_pin_number=dto.gpio_pin_number,
            name=dto.name,
            default_value_when_closed=dto.default_value_when_closed,
            listening=False,
            group_id=None,
        )
