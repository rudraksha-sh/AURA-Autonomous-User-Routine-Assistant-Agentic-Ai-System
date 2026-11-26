"""Create isolated AURA runtime and migrator roles in a managed PostgreSQL DB.

Run once with DATABASE_ADMIN_URL, AURA_RUNTIME_DB_PASSWORD and
AURA_MIGRATOR_DB_PASSWORD in an ephemeral private operator environment.
"""
import os
import psycopg
from psycopg import sql


def main() -> None:
    admin_url = os.environ["DATABASE_ADMIN_URL"]
    runtime_password = os.environ["AURA_RUNTIME_DB_PASSWORD"]
    migrator_password = os.environ["AURA_MIGRATOR_DB_PASSWORD"]
    if runtime_password == migrator_password or min(len(runtime_password), len(migrator_password)) < 32:
        raise SystemExit("Database role passwords must be distinct and at least 32 characters.")

    with psycopg.connect(admin_url, autocommit=True) as connection:
        for role, password in (("aura_runtime", runtime_password), ("aura_migrator", migrator_password)):
            exists = connection.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
            statement = sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(role), sql.Literal(password)
            ) if exists else sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(role), sql.Literal(password)
            )
            connection.execute(statement)
        database = connection.execute("SELECT current_database()").fetchone()[0]
        connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO aura_runtime, aura_migrator").format(
            sql.Identifier(database)
        ))
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        connection.execute("GRANT USAGE ON SCHEMA public TO aura_runtime")
        connection.execute("GRANT USAGE, CREATE ON SCHEMA public TO aura_migrator")
        if connection.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0]:
            connection.execute("GRANT SELECT ON TABLE alembic_version TO aura_runtime")
        connection.execute(sql.SQL(
            "ALTER DEFAULT PRIVILEGES FOR ROLE aura_migrator IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aura_runtime"
        ))
        connection.execute(sql.SQL(
            "ALTER DEFAULT PRIVILEGES FOR ROLE aura_migrator IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO aura_runtime"
        ))
        print("Database extension and least-privilege roles provisioned.")


if __name__ == "__main__":
    main()
