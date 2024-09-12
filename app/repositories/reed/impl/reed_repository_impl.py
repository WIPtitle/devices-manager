from typing import Sequence

from sqlmodel import select

from app.database.database_connector import DatabaseConnector
from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.not_found_exception import NotFoundException
from app.models.reed import Reed
from app.repositories.reed.reed_repository import ReedRepository


class ReedRepositoryImpl(ReedRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector


    def find_by_gpio_pin_number(self, reed_gpio_pin_number: int) -> Reed:
        statement = select(Reed).where(Reed.gpio_pin_number == reed_gpio_pin_number)
        reed_db = self.database_connector.get_session().exec(statement).first()
        if reed_db is None:
            raise NotFoundException("Reed was not found")

        return reed_db


    def create(self, reed: Reed) -> Reed:
        try:
            self.find_by_gpio_pin_number(reed.gpio_pin_number)
        except NotFoundException:
            self.database_connector.get_session().add(reed)
            self.database_connector.get_session().commit()
            self.database_connector.get_session().refresh(reed)
            return reed
        raise BadRequestException("Reed already exists")



    def update(self, reed: Reed) -> Reed:
        reed_db = self.find_by_gpio_pin_number(reed.gpio_pin_number)
        reed_db.default_value_when_closed = reed.default_value_when_closed
        self.database_connector.get_session().commit()
        self.database_connector.get_session().refresh(reed_db)
        return reed_db


    def delete_by_gpio_pin_number(self, reed_gpio_pin_number: int) -> Reed:
        reed_db = self.find_by_gpio_pin_number(reed_gpio_pin_number)
        self.database_connector.get_session().delete(reed_db)
        self.database_connector.get_session().commit()
        return reed_db


    def find_all(self) -> Sequence[Reed]:
        statement = select(Reed)
        return self.database_connector.get_session().exec(statement).all()
