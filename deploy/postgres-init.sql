\set runtime_password `cat /run/secrets/runtime_db_password`
\set migration_password `cat /run/secrets/migration_db_password`
SELECT format('CREATE ROLE aura_runtime LOGIN PASSWORD %L', :'runtime_password') \gexec
SELECT format('CREATE ROLE aura_migrator LOGIN PASSWORD %L', :'migration_password') \gexec

CREATE EXTENSION IF NOT EXISTS vector;
REVOKE ALL ON DATABASE aura FROM PUBLIC;
GRANT CONNECT ON DATABASE aura TO aura_runtime, aura_migrator;
ALTER SCHEMA public OWNER TO aura_migrator;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO aura_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE aura_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aura_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE aura_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO aura_runtime;
