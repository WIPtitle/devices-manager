from sqlmodel import SQLModel, Field

from app.exceptions.validation_exception import ValidationException
from app.models.enums.reed_status import ReedStatus


class Reed(SQLModel, table=True):
    gpio_pin_number: int = Field(primary_key=True)
    default_value_when_closed: ReedStatus

    # To create object both with string value of enum reedstatus and with reedstatus
    def __init__(self, gpio_pin_number: int, default_value_when_closed: str):
        if not isinstance(default_value_when_closed, ReedStatus):
            if default_value_when_closed in ReedStatus.__members__.values():
                default_value_when_closed = ReedStatus(default_value_when_closed)
            else:
                raise ValidationException(f"Invalid value for ReedStatus: {default_value_when_closed}")
        super().__init__(gpio_pin_number=gpio_pin_number, default_value_when_closed=default_value_when_closed)