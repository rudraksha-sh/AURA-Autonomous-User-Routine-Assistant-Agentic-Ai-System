import runpy
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

from alembic import command, context
from alembic.config import Config
from sqlalchemy import URL

from app.core.config import settings


BACKEND = Path(__file__).resolve().parents[1]
FIXTURE_PASSWORD = "synthetic@:%/fixture"


def test_migration_cli_and_alembic_preserve_url_credentials(monkeypatch):
    source = URL.create(
        "postgresql+psycopg",
        username="fixture",
        password=FIXTURE_PASSWORD,
        host="db.example.test",
        database="fixture",
        query={"connect_timeout": "3", "sslmode": "require"},
    )
    original = source.render_as_string(hide_password=False)
    monkeypatch.setattr(settings, "database_url", original)
    monkeypatch.setattr(settings, "database_ssl_mode", "verify-full")
    monkeypatch.setattr(settings, "database_ssl_root_cert", "/fixtures/root ca.pem")
    monkeypatch.setattr(sys, "argv", ["migrate.py", "upgrade"])
    for key in ("ENVIRONMENT", "JWT_SECRET_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "AI_PROVIDER"):
        monkeypatch.setenv(key, "fixture")

    upgrade = Mock()
    monkeypatch.setattr(command, "upgrade", upgrade)
    runpy.run_path(str(BACKEND / "ops/migrate.py"), run_name="__main__")
    upgrade.assert_called_once()
    assert upgrade.call_args.args[1] == "head"
    assert settings.database_url == original

    # Exercise the URL actually handed to Alembic's online engine factory.
    factory = MagicMock()
    monkeypatch.setattr("sqlalchemy.engine_from_config", factory)
    monkeypatch.setattr(context, "config", Config(), raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: False, raising=False)
    monkeypatch.setattr(context, "configure", Mock(), raising=False)
    monkeypatch.setattr(context, "begin_transaction", MagicMock(), raising=False)
    monkeypatch.setattr(context, "run_migrations", Mock(), raising=False)
    runpy.run_path(str(BACKEND / "alembic/env.py"))
    url = factory.call_args.kwargs["url"]
    assert url.password == FIXTURE_PASSWORD
    assert url.query == {
        "connect_timeout": "3",
        "sslmode": "verify-full",
        "sslrootcert": "/fixtures/root ca.pem",
    }
