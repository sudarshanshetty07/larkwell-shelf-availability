# Lakebase: operational serving and the loop back to Unity Catalog

_Generated 2026-10-19 08:08 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

## Serving: gold synced into Postgres for Shelf Scan

- Synced table `larkwell_osa_pg.serving.product_location_status`: state `SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE`, last sync "2026-10-19T01:28:36.174494Z"
- Rows in Postgres (read through Unity Catalog): 5,400,000, of which 205,834 are gaps or lows
- Primary key (store, upc): every Shelf Scan is a point lookup

## Operational writes and Lakehouse Sync back to Unity Catalog

The app writes colleague actions, scan telemetry, AI recommendations and Genie feedback to the `ops` schema in Lakebase. Lakehouse Sync (config `ops_to_lakehouse`) streams every change into `larkwell_osa.ops.lb_<table>_history`.

| lakebase_table | changes_in_unity_catalog |
|---|---|
| colleague_actions | 16 |
| scan_log | 488 |
| ai_recommendations | 31 |
| genie_feedback | 15 |

## Latest scans recorded (from larkwell_osa.gold.shelf_scans)

| scanned (UTC) | store | status | root_cause | served_by | lookup_ms |
|---|---|---|---|---|---|
| 2026-10-19 02:54:31 | Barnstaple | NO_ISSUE |  | lakebase | 2.6 |
| 2026-10-19 02:54:31 | Chester High Street | NO_ISSUE |  | lakebase | 2.4 |
| 2026-10-19 02:54:31 | Aberdeen Station | NO_ISSUE |  | lakebase | 2.5 |
| 2026-10-19 02:54:31 | Angel High Street | NO_ISSUE |  | lakebase | 94.3 |
| 2026-10-19 02:54:31 | Bristol High Street | NO_ISSUE |  | lakebase | 3.9 |
| 2026-10-19 02:54:31 | Canterbury | NO_ISSUE |  | lakebase | 2.5 |
| 2026-10-19 02:54:30 | Wigan | NO_ISSUE |  | lakebase | 2.3 |
| 2026-10-19 02:54:30 | Ruislip | NO_ISSUE |  | lakebase | 2.4 |
| 2026-10-19 02:54:30 | Banbury Local | NO_ISSUE |  | lakebase | 2.2 |
| 2026-10-19 02:54:30 | Goole Local | NO_ISSUE |  | lakebase | 2.3 |

## Lookup speed by serving path (from the app's own scan log)

| served_by | scans | p50_ms | p95_ms |
|---|---|---|---|
| lakebase | 381 | 2.6 | 4.3 |
| warehouse | 107 | 629.3 | 729.7 |
