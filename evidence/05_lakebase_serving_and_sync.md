# Lakebase: operational serving and the loop back to Unity Catalog

_Generated 2026-10-18 14:18 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

## Serving: gold synced into Postgres for Shelf Scan

- Synced table `larkwell_osa_pg.serving.product_location_status`: state `SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE`, last sync "2026-10-18T12:56:37.209174Z"
- Rows in Postgres (read through Unity Catalog): 5,400,000, of which 205,834 are gaps or lows
- Primary key (store, upc): every Shelf Scan is a point lookup

## Operational writes and Lakehouse Sync back to Unity Catalog

The app writes colleague actions, scan telemetry, AI recommendations and Genie feedback to the `ops` schema in Lakebase. Lakehouse Sync (config `ops_to_lakehouse`) streams every change into `larkwell_osa.ops.lb_<table>_history`.

| lakebase_table | changes_in_unity_catalog |
|---|---|
| colleague_actions | 5 |
| scan_log | 377 |
| ai_recommendations | 16 |
| genie_feedback | 13 |

## Latest scans recorded (from larkwell_osa.gold.shelf_scans)

| scanned (UTC) | store | status | root_cause | served_by | lookup_ms |
|---|---|---|---|---|---|
| 2026-10-18 14:17:43 | Oxford Outlet | NO_ISSUE |  | lakebase | 3.7 |
| 2026-10-18 14:17:43 | Bury Local | ISSUE_FOUND | UNDER_FORECAST | lakebase | 2.8 |
| 2026-10-18 14:17:43 | Winchester High Street | NO_ISSUE |  | lakebase | 13.2 |
| 2026-10-18 14:17:43 | Chorlton Station | NO_ISSUE |  | lakebase | 2.9 |
| 2026-10-18 14:17:43 | Dundee Station | NO_ISSUE |  | lakebase | 4.1 |
| 2026-10-18 14:17:43 | Berwick-upon-Tweed Retail Park | NO_ISSUE |  | lakebase | 2.8 |
| 2026-10-18 14:17:43 | Poole Superstore | NO_ISSUE |  | lakebase | 2.9 |
| 2026-10-18 14:17:42 | Durham | NO_ISSUE |  | lakebase | 2.7 |
| 2026-10-18 14:17:42 | Keswick Local | NO_ISSUE |  | lakebase | 3.0 |
| 2026-10-18 14:17:42 | Troon Station | NO_ISSUE |  | lakebase | 6.9 |

## Lookup speed by serving path (from the app's own scan log)

| served_by | scans | p50_ms | p95_ms |
|---|---|---|---|
| lakebase | 292 | 2.7 | 4.3 |
| warehouse | 85 | 559.9 | 719.6 |
