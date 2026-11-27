#!/usr/bin/env bash
# Creates the Semraa databases and roles. The app role does not own tables and has no BYPASSRLS;
# migrations run as the separate owner role (Engineering Standards, section 5).
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" \
  -v migrator_pw="$SEMRAA_MIGRATOR_PASSWORD" \
  -v app_pw="$SEMRAA_APP_PASSWORD" \
  -v keycloak_pw="$KEYCLOAK_DB_PASSWORD" <<'SQL'
CREATE ROLE semraa_migrator LOGIN PASSWORD :'migrator_pw' NOBYPASSRLS;
CREATE ROLE semraa_app LOGIN PASSWORD :'app_pw' NOBYPASSRLS NOCREATEDB NOCREATEROLE;
CREATE DATABASE semraa OWNER semraa_migrator;
CREATE ROLE keycloak LOGIN PASSWORD :'keycloak_pw';
CREATE DATABASE keycloak OWNER keycloak;
\connect semraa
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
GRANT CONNECT ON DATABASE semraa TO semraa_app;
SQL
