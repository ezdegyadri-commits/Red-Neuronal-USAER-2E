#!/bin/sh
(
    set -eu
    PG_OWNER_SECRET=$(cat /run/secrets/pg_owner)
    PG_RUNTIME_SECRET=$(cat /run/secrets/pg_runtime)
    export PG_OWNER_SECRET PG_RUNTIME_SECRET
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv owner_password PG_OWNER_SECRET
\getenv runtime_password PG_RUNTIME_SECRET
CREATE ROLE spa_fixture_oracle LOGIN PASSWORD :'owner_password';
CREATE ROLE spa_runtime_oracle LOGIN PASSWORD :'runtime_password';
ALTER DATABASE usaer_spa_test_oracle OWNER TO spa_fixture_oracle;
COMMENT ON DATABASE usaer_spa_test_oracle IS 'USAER SPA synthetic only';
REVOKE ALL ON DATABASE usaer_spa_test_oracle FROM PUBLIC;
GRANT CONNECT ON DATABASE usaer_spa_test_oracle TO spa_runtime_oracle;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO spa_runtime_oracle;
ALTER DEFAULT PRIVILEGES FOR ROLE spa_fixture_oracle IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO spa_runtime_oracle;
SQL
)
