import os
import time

from sqlmodel import Session, create_engine, SQLModel

from app.database.database_connector import DatabaseConnector
from app.database.migration_runner import MigrationRunner
from app.utils.read_credentials import read_credentials


class DatabaseConnectorImpl(DatabaseConnector):
    def __init__(self):
        database_hostname = "db"
        credentials_file = os.getenv('PG_CREDENTIALS_FILE')
        credentials = read_credentials(credentials_file)

        self.engine = create_engine(
            f"postgresql://{credentials['POSTGRES_USER']}:{credentials['POSTGRES_PASSWORD']}@{database_hostname}:5432/{credentials['POSTGRES_DB']}",
            echo=False)

        for attempt in range(10):
            try:
                SQLModel.metadata.create_all(self.engine)
                break
            except Exception as e:
                print(f"Database not ready (attempt {attempt + 1}/10): {e}")
                time.sleep(2)
        else:
            raise RuntimeError("Failed to connect to database after 10 attempts")

        try:
            migration_runner = MigrationRunner(self.engine)
            migration_runner.run()
        except Exception as e:
            print(f"Warning: database migration failed: {e}")

    def get_new_session(self):
        return Session(self.engine)
