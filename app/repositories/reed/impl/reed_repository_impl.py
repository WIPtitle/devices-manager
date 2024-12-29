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
        session = self.database_connector.get_new_session()
        reed_db = session.exec(statement).first()
        session.close()
        if reed_db is None:
            raise NotFoundException("Reed was not found")

        return reed_db


    def create(self, reed: Reed) -> Reed:
        try:
            self.find_by_gpio_pin_number(reed.gpio_pin_number)
        except NotFoundException:
            session = self.database_connector.get_new_session()
            session.add(reed)
            session.commit()
            session.refresh(reed)
            session.close()
            return reed
        raise BadRequestException("Reed already exists")


    def update(self, reed: Reed) -> Reed:
        statement = select(Reed).where(Reed.gpio_pin_number == reed.gpio_pin_number)
        session = self.database_connector.get_new_session()
        reed_db = session.exec(statement).first()
        if reed_db is None:
            raise NotFoundException("Reed was not found")

        reed_db.vcc = reed.vcc
        reed_db.normally_closed = reed.normally_closed
        reed_db.name = reed.name
        session.commit()
        session.refresh(reed_db)
        session.close()
        return reed_db


    def delete_by_gpio_pin_number(self, reed_gpio_pin_number: int) -> Reed:
        statement = select(Reed).where(Reed.gpio_pin_number == reed_gpio_pin_number)
        session = self.database_connector.get_new_session()
        reed_db = session.exec(statement).first()
        if reed_db is None:
            raise NotFoundException("Reed was not found")

        session.delete(reed_db)
        session.commit()
        session.close()
        return reed_db


    def find_all(self) -> Sequence[Reed]:
        statement = select(Reed)
        session = self.database_connector.get_new_session()
        result = session.exec(statement).all()
        session.close()
        return result


    def update_listening(self, reed: Reed, listening: bool):
        statement = select(Reed).where(Reed.gpio_pin_number == reed.gpio_pin_number)
        session = self.database_connector.get_new_session()
        reed_db = session.exec(statement).first()
        if reed_db is None:
            raise NotFoundException("Reed was not found")

        reed_db.listening = listening
        session.commit()
        session.refresh(reed_db)
        session.close()
        return reed_db
