-- Least-privilege Unity Catalog grants for the app's service principal (replace <app_sp> with its client id).
-- Read-only on gold, ops and ml (the gap-risk predictions). The app has no write access to the lakehouse: its writes
-- go to Lakebase, and Lakehouse Sync brings them back into ops.
GRANT USE CATALOG ON CATALOG larkwell_osa TO `<app_sp>`;
GRANT USE SCHEMA, SELECT ON SCHEMA larkwell_osa.gold TO `<app_sp>`;
GRANT USE SCHEMA, SELECT ON SCHEMA larkwell_osa.ops TO `<app_sp>`;
GRANT USE SCHEMA, SELECT ON SCHEMA larkwell_osa.ml TO `<app_sp>`;
