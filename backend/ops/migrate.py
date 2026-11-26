"""One-shot migration command with only the migration database secret."""
import os
from pathlib import Path
import secrets
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ.update(
    ENVIRONMENT="maintenance",
    JWT_SECRET_KEY=secrets.token_urlsafe(48),
    GOOGLE_CLIENT_ID="",
    GOOGLE_CLIENT_SECRET="",
    AI_PROVIDER="disabled",
)

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import make_url, text

from app.core.config import settings
from app.db.session import engine


if __name__ == "__main__":
    if make_url(settings.database_url).get_backend_name() != "postgresql":
        raise SystemExit("Production migrations require PostgreSQL.")
    config = Config(root / "alembic.ini")
    operation = sys.argv[1:] or ["upgrade"]
    match operation:
        case ["upgrade"]:
            command.upgrade(config, "head")
        case ["current"]:
            command.current(config)
        case ["verify"]:
            head = ScriptDirectory.from_config(config).get_current_head()
            with engine.connect() as connection:
                revisions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            if revisions != [head]:
                raise SystemExit("Database revision does not match this build")
            print(f"Database revision verified: {head}")
        case ["check"]:
            command.check(config)
        case _:
            raise SystemExit("Usage: migrate.py [upgrade|current|check|verify]")
