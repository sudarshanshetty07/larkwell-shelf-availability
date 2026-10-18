-- Lakebase grants for the app's service principal. Run as the project owner:
--   databricks psql --project larkwell-osa --profile <profile> -- -d databricks_postgres -v sp=<app_sp_client_id> -f lakebase/grants.sql
-- Read-only on the synced serving table; read, insert and update (no delete) on the app's operational tables.
GRANT USAGE ON SCHEMA serving TO :"sp";
GRANT SELECT ON ALL TABLES IN SCHEMA serving TO :"sp";
GRANT USAGE ON SCHEMA ops TO :"sp";
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ops TO :"sp";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ops TO :"sp";
