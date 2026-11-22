# Cleanup report

No tracked or pre-existing local files were removed. Existing backups, migrations, documentation, fixtures, environment files and user data were retained. No pre-existing database was reset.

Ignore rules now cover TypeScript metadata, Ruff and mypy caches and local `.envrc` files. Existing rules continue to protect local environment files, databases, uploads and build artifacts.

Tests use isolated SQLite by default. Opt-in PostgreSQL testing creates and removes only its own randomly named schema. Migration verification used a disposable local PostgreSQL cluster.
