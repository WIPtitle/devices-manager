from typing import Sequence, Optional

from sqlmodel import select

from app.database.database_connector import DatabaseConnector
from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.not_found_exception import NotFoundException
from app.models.system_config import SystemConfig, GpioServer, Mp3Server
from app.repositories.system_config.system_config_repository import SystemConfigRepository


class SystemConfigRepositoryImpl(SystemConfigRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector

    def get_all_config(self) -> Sequence[SystemConfig]:
        session = self.database_connector.get_new_session()
        configs = session.exec(select(SystemConfig)).all()
        session.close()
        return configs

    def get_config(self, key: str) -> Optional[str]:
        session = self.database_connector.get_new_session()
        config = session.exec(select(SystemConfig).where(SystemConfig.key == key)).first()
        session.close()
        return config.value if config else None

    def set_config(self, key: str, value: str):
        session = self.database_connector.get_new_session()
        config = session.exec(select(SystemConfig).where(SystemConfig.key == key)).first()
        if config:
            config.value = value
        else:
            session.add(SystemConfig(key=key, value=value))
        session.commit()
        session.close()

    def get_all_gpio_servers(self) -> Sequence[GpioServer]:
        session = self.database_connector.get_new_session()
        servers = session.exec(select(GpioServer)).all()
        session.close()
        return servers

    def create_gpio_server(self, server: GpioServer) -> GpioServer:
        session = self.database_connector.get_new_session()
        existing = session.exec(select(GpioServer).where(GpioServer.url == server.url)).first()
        if existing:
            session.close()
            raise BadRequestException(f"GPIO server with URL {server.url} already exists")
        session.add(server)
        session.commit()
        session.refresh(server)
        session.close()
        return server

    def delete_gpio_server(self, server_id: int):
        session = self.database_connector.get_new_session()
        server = session.exec(select(GpioServer).where(GpioServer.id == server_id)).first()
        if not server:
            session.close()
            raise NotFoundException("GPIO server not found")
        session.delete(server)
        session.commit()
        session.close()

    def get_all_mp3_servers(self) -> Sequence[Mp3Server]:
        session = self.database_connector.get_new_session()
        servers = session.exec(select(Mp3Server)).all()
        session.close()
        return servers

    def create_mp3_server(self, server: Mp3Server) -> Mp3Server:
        session = self.database_connector.get_new_session()
        existing = session.exec(select(Mp3Server).where(Mp3Server.url == server.url)).first()
        if existing:
            session.close()
            raise BadRequestException(f"MP3 server with URL {server.url} already exists")
        session.add(server)
        session.commit()
        session.refresh(server)
        session.close()
        return server

    def update_mp3_server(self, server: Mp3Server) -> Mp3Server:
        session = self.database_connector.get_new_session()
        existing = session.exec(select(Mp3Server).where(Mp3Server.id == server.id)).first()
        if not existing:
            session.close()
            raise NotFoundException("MP3 server not found")
        existing.url = server.url
        existing.audio_type_alarm = server.audio_type_alarm
        existing.audio_type_waiting = server.audio_type_waiting
        existing.audio_type_warning = server.audio_type_warning
        existing.volume_alarm = server.volume_alarm
        existing.volume_waiting = server.volume_waiting
        existing.volume_warning = server.volume_warning
        session.commit()
        session.refresh(existing)
        session.close()
        return existing

    def delete_mp3_server(self, server_id: int):
        session = self.database_connector.get_new_session()
        server = session.exec(select(Mp3Server).where(Mp3Server.id == server_id)).first()
        if not server:
            session.close()
            raise NotFoundException("MP3 server not found")
        session.delete(server)
        session.commit()
        session.close()
