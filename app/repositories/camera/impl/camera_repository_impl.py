from typing import Sequence

from sqlmodel import select

from app.database.database_connector import DatabaseConnector
from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.not_found_exception import NotFoundException
from app.models.camera import Camera
from app.repositories.camera.camera_repository import CameraRepository


class CameraRepositoryImpl(CameraRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector


    def find_by_ip(self, ip: str) -> Camera:
        statement = select(Camera).where(Camera.ip == ip)
        session = self.database_connector.get_new_session()
        camera_db = session.exec(statement).first()
        session.close()
        if camera_db is None:
            raise NotFoundException("Camera was not found")

        return camera_db


    def create(self, camera: Camera) -> Camera:
        try:
            self.find_by_ip(camera.ip)
        except NotFoundException:
            session = self.database_connector.get_new_session()
            session.add(camera)
            session.commit()
            session.refresh(camera)
            session.close()
            return camera
        raise BadRequestException("Camera already exists")


    def update(self, camera: Camera) -> Camera:
        statement = select(Camera).where(Camera.ip == camera.ip)
        session = self.database_connector.get_new_session()
        camera_db = session.exec(statement).first()
        if camera_db is None:
            raise NotFoundException("Camera was not found")

        camera_db.port = camera.port
        camera_db.username = camera.username
        camera_db.password = camera.password
        camera_db.path = camera.path
        camera_db.sensibility = camera.sensibility
        camera_db.name = camera.name

        session.commit()
        session.refresh(camera_db)
        session.close()
        return camera_db


    def delete_by_ip(self, ip: str) -> Camera:
        statement = select(Camera).where(Camera.ip == ip)
        session = self.database_connector.get_new_session()
        camera_db = session.exec(statement).first()
        if camera_db is None:
            raise NotFoundException("Camera was not found")
        session.delete(camera_db)
        session.commit()
        session.close()
        return camera_db


    def find_all(self) -> Sequence[Camera]:
        statement = select(Camera)
        session = self.database_connector.get_new_session()
        result = session.exec(statement).all()
        session.close()
        return result


    def update_listening(self, camera: Camera, listening: bool):
        statement = select(Camera).where(Camera.ip == camera.ip)
        session = self.database_connector.get_new_session()
        camera_db = session.exec(statement).first()
        if camera_db is None:
            raise NotFoundException("Camera was not found")
        camera_db.listening = listening
        session.commit()
        session.refresh(camera_db)
        session.close()
        return camera_db