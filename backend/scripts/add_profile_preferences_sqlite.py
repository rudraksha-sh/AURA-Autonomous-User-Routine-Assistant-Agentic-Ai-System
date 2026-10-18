"""Additive schema update for the repository's development SQLite database.

Production databases must use Alembic. This helper only adds missing columns
to backend/aura_dev.db and never rewrites existing account records.
"""
from pathlib import Path

from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.session import engine


DEVELOPMENT_DATABASE = (Path(__file__).resolve().parents[1] / "aura_dev.db").resolve()
ADDITIVE_COLUMNS = {
    "role": "VARCHAR(20) NOT NULL DEFAULT 'user'",
    "profile_photo_filename": "VARCHAR(64)",
    "theme_preference": "VARCHAR(10) NOT NULL DEFAULT 'system'",
}


def main() -> None:
    if settings.environment.lower() not in {"development", "dev"} or engine.dialect.name != "sqlite":
        raise SystemExit("Refusing to run: this helper is only for a development SQLite database.")
    database_path = Path(engine.url.database or "").resolve()
    if database_path != DEVELOPMENT_DATABASE or not database_path.is_file():
        raise SystemExit(f"Refusing to modify unexpected database: {database_path}")

    with engine.begin() as connection:
        tables = inspect(connection).get_table_names()
        if "users" not in tables:
            raise SystemExit("The users table does not exist; start the app once to initialize the development database.")
        existing = {column["name"] for column in inspect(connection).get_columns("users")}
        for name, definition in ADDITIVE_COLUMNS.items():
            if name not in existing:
                connection.execute(text(f'ALTER TABLE users ADD COLUMN "{name}" {definition}'))
                print(f"Added users.{name}")
            else:
                print(f"users.{name} already exists")


if __name__ == "__main__":
    main()
