import os
from pathlib import Path

from sqlalchemy import text


class MigrationRunner:
    def __init__(self, engine):
        self.engine = engine
        self.migrations_dir = Path(os.path.dirname(__file__)) / "migrations"

    def run(self):
        self._ensure_migrations_table()
        applied = self._get_applied_migrations()
        pending = self._get_pending_migrations(applied)

        if not pending:
            print("Database migrations: all up to date")
            return

        for version, migration_file in pending:
            self._apply_migration(version, migration_file)

    def _ensure_migrations_table(self):
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()

    def _get_applied_migrations(self) -> set:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM _migrations"))
            return {row[0] for row in result}

    def _get_pending_migrations(self, applied: set) -> list:
        if not self.migrations_dir.exists():
            return []

        migration_files = sorted(self.migrations_dir.glob("V*.sql"))
        pending = []
        for migration_file in migration_files:
            version = migration_file.stem
            if version not in applied:
                pending.append((version, migration_file))
        return pending

    def _apply_migration(self, version: str, migration_file: Path):
        sql = migration_file.read_text()
        print(f"Applying migration: {version}")
        with self.engine.connect() as conn:
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))
            conn.execute(
                text("INSERT INTO _migrations (version) VALUES (:v)"),
                {"v": version}
            )
            conn.commit()
        print(f"Migration {version} applied successfully")
