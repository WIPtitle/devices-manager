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
        camera_db = self.database_connector.get_new_session().exec(statement).first()
        if camera_db is None:
            raise NotFoundException("Camera was not found")

        return camera_db


    def create(self, camera: Camera) -> Camera:
        try:
            self.find_by_ip(camera.ip)
        except NotFoundException:
            self.database_connector.get_new_session().add(camera)
            self.database_connector.get_new_session().commit()
            self.database_connector.get_new_session().refresh(camera)
            return camera
        raise BadRequestException("Camera already exists")



    def update(self, camera: Camera) -> Camera:
        camera_db = self.find_by_ip(camera.ip)
        camera_db.port = camera.port
        camera_db.username = camera.username
        camera_db.password = camera.password
        camera_db.path = camera.path
        camera_db.sensibility = camera.sensibility
        camera_db.name = camera.name
        self.database_connector.get_new_session().commit()
        self.database_connector.get_new_session().refresh(camera_db)
        return camera_db


    def delete_by_ip(self, ip: str) -> Camera:
        camera_db = self.find_by_ip(ip)
        self.database_connector.get_new_session().delete(camera_db)
        self.database_connector.get_new_session().commit()
        return camera_db


    def find_all(self) -> Sequence[Camera]:
        statement = select(Camera)
        return self.database_connector.get_new_session().exec(statement).all()


    def update_listening(self, camera: Camera, listening: bool):
        camera_db = self.find_by_ip(camera.ip)
        camera_db.listening = listening
        self.database_connector.get_new_session().commit()
        self.database_connector.get_new_session().refresh(camera_db)
        return camera_db