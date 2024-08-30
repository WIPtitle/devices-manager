from abc import abstractmethod, ABC

from sqlalchemy.orm import Session


class DatabaseConnector(ABC):
    @abstractmethod
    def get_db(self) -> Session:
        pass