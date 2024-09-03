import os

from sqlmodel import Session, create_engine, SQLModel
from app.database.database_connector import DatabaseConnector
from app.utils.read_credentials import read_credentials


class DatabaseConnectorImpl(DatabaseConnector):
    def __init__(self):
        database_hostname = os.getenv('DATABASE_HOSTNAME')
        credentials_file = os.getenv('PG_CREDENTIALS_FILE')
        credentials = read_credentials(credentials_file)

        self.session = None
        self.engine = create_engine(
            f"postgresql://{credentials['POSTGRES_USER']}:{credentials['POSTGRES_PASSWORD']}@{database_hostname}:5432/{credentials['POSTGRES_DB']}",
            echo=True)

        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        if self.session is None or not self.session.is_active:
            if self.session is not None:
                self.session.rollback()
                self.session.close()
            self.session = Session(self.engine)
        return self.session