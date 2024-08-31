from sqlmodel import SQLModel, Field


class GpioConfig(SQLModel, table=True):
    id: int = Field(primary_key=True)
    default_value_when_closed: int
