import os
import secrets

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import pytest

from ops import bootstrap_database


def test_postgres17_migrator_default_privileges(monkeypatch):
    admin_url = os.environ.get("AURA_BOOTSTRAP_TEST_ADMIN_URL")
    if not admin_url:
        pytest.skip("Requires an isolated PostgreSQL 17 cluster with pgvector")
    options = conninfo_to_dict(admin_url)
    assert options.get("host") in {"127.0.0.1", "::1"}
    assert options.get("port") and options["port"] != "5432"
    assert options.get("dbname") == "aura_bootstrap_test"

    with psycopg.connect(admin_url) as admin:
        assert admin.info.server_version // 10000 == 17
        assert admin.execute(
            "SELECT rolsuper, rolcreaterole FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == (False, True)
        assert not admin.execute(
            "SELECT 1 FROM pg_roles WHERE rolname IN ('aura_runtime', 'aura_migrator')"
        ).fetchone()

    runtime_password, migrator_password = (secrets.token_urlsafe(48) for _ in range(2))
    monkeypatch.setenv("DATABASE_ADMIN_URL", admin_url)
    monkeypatch.setenv("AURA_RUNTIME_DB_PASSWORD", runtime_password)
    monkeypatch.setenv("AURA_MIGRATOR_DB_PASSWORD", migrator_password)
    bootstrap_database.main()

    migrator_url = make_conninfo(admin_url, user="aura_migrator", password=migrator_password)
    with psycopg.connect(migrator_url) as migrator:
        migrator.execute("CREATE TABLE public.bootstrap_probe (id serial PRIMARY KEY, value text)")

    runtime_url = make_conninfo(admin_url, user="aura_runtime", password=runtime_password)
    with psycopg.connect(runtime_url) as runtime:
        assert runtime.execute(
            "SELECT rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == (False, False, False)
        assert runtime.execute(
            "SELECT has_schema_privilege(current_user, 'public', 'CREATE')"
        ).fetchone() == (False,)
        assert runtime.execute(
            "INSERT INTO public.bootstrap_probe (value) VALUES ('fixture') RETURNING id"
        ).fetchone() == (1,)
        assert runtime.execute(
            "UPDATE public.bootstrap_probe SET value = 'updated' WHERE id = 1 RETURNING value"
        ).fetchone() == ("updated",)
        assert runtime.execute("DELETE FROM public.bootstrap_probe WHERE id = 1").rowcount == 1
