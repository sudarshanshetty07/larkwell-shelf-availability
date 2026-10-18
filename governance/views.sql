-- Governed views over the Lakebase change history that Lakehouse Sync streams into Unity Catalog.
-- They expose what happened in stores without exposing who did it: actor emails stay in ops, which only the app can read.

CREATE OR REPLACE VIEW larkwell_osa.gold.colleague_actions
COMMENT 'What store colleagues did about gaps and lows: the current state of every action logged in the Shelf Availability app. Built from the Lakebase change history (Lakehouse Sync), so new actions appear within about a minute. No personal data.'
AS SELECT action_id, business_date, store, upc, product, issue, root_cause, action_type, note, status, persona, created_at, updated_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY action_id ORDER BY _pg_lsn DESC) AS rn
  FROM larkwell_osa.ops.lb_colleague_actions_history
  WHERE _pg_change_type IN ('insert', 'update_postimage', 'delete')
)
WHERE rn = 1 AND _pg_change_type <> 'delete';

CREATE OR REPLACE VIEW larkwell_osa.gold.shelf_scans
COMMENT 'Every Shelf Scan lookup made in the app: store, product, the answer given, which system served it and how long it took. From the Lakebase change history (Lakehouse Sync). No personal data.'
AS SELECT scan_id, scanned_at, store, upc, status, issue, root_cause, served_by, lookup_ms
FROM larkwell_osa.ops.lb_scan_log_history
WHERE _pg_change_type = 'insert';
