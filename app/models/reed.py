from sqlmodel import SQLModel, Field

from app.models.enums.gpio_value import GpioValue


class Reed(SQLModel, table=True):
    gpio_pin_number: int = Field(primary_key=True)
    default_value_when_closed: GpioValue


    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other
