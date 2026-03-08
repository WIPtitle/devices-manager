from abc import abstractmethod
from typing import Sequence

from app.models.system_config import GpioServer, Mp3Server


class SystemConfigService:
    @abstractmethod
    def get_all_config(self) -> dict:
        pass

    @abstractmethod
    def update_config(self, key: str, value: str):
        pass

    @abstractmethod
    def get_all_gpio_servers(self) -> Sequence[GpioServer]:
        pass

    @abstractmethod
    def create_gpio_server(self, server: GpioServer) -> GpioServer:
        pass

    @abstractmethod
    def delete_gpio_server(self, server_id: int):
        pass

    @abstractmethod
    def get_all_mp3_servers(self) -> Sequence[Mp3Server]:
        pass

    @abstractmethod
    def create_mp3_server(self, server: Mp3Server) -> Mp3Server:
        pass

    @abstractmethod
    def update_mp3_server(self, server: Mp3Server) -> Mp3Server:
        pass

    @abstractmethod
    def delete_mp3_server(self, server_id: int):
        pass
