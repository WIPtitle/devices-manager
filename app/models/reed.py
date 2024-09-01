from sqlmodel import SQLModel, Field


class Reed(SQLModel, table=True):
    gpio_pin_number: int = Field(primary_key=True)
    default_value_when_closed: int
