# Daily checks on every stage of the data journey

_Generated 2026-10-19 08:08 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

`data/02_validate_and_publish.py` runs after every pipeline update and Lakebase refresh. It checks each stage of the journey, including the gap-risk model's inputs, and publishes the results to `ops.pipeline_checks`, which the app's Data Journey tab reads. The job fails if any check fails.

## Every check run

| run at (UTC) | business date | passed | note |
|---|---|---|---|
| 2026-10-18 11:16:22 | 2026-10-17 | 40 of 40 | Checked the earlier version of this day, when every simulated day shared one seed. The day was later regenerated as part of the five-week history (`docs/decisions.md` §16); history days are checked against their manifests and answer keys before training (`10_gap_risk_model.md`). |
| 2026-10-18 12:01:04 | 2026-10-18 | 32 of 37 | Checked the earlier version of this day, when every simulated day shared one seed. The day was later regenerated as part of the five-week history (`docs/decisions.md` §16); history days are checked against their manifests and answer keys before training (`10_gap_risk_model.md`). |
| 2026-10-18 12:02:32 | 2026-10-18 | 32 of 37 | Checked the earlier version of this day, when every simulated day shared one seed. The day was later regenerated as part of the five-week history (`docs/decisions.md` §16); history days are checked against their manifests and answer keys before training (`10_gap_risk_model.md`). |
| 2026-10-18 12:10:20 | 2026-10-17 | 40 of 40 | Doesn't count. A job repair wasn't given the business date, so it checked the default, 2026-10-17, while gold held 2026-10-18. It passed only because the synthetic days share a seed. Validation now refuses to check a different day from the one gold holds (`09_daily_job_runs.md`). |
| 2026-10-18 12:41:27 | 2026-10-18 | 36 of 40 | Checked the earlier version of this day, when every simulated day shared one seed. The day was later regenerated as part of the five-week history (`docs/decisions.md` §16); history days are checked against their manifests and answer keys before training (`10_gap_risk_model.md`). |
| 2026-10-18 12:43:06 | 2026-10-18 | 36 of 40 | Checked the earlier version of this day, when every simulated day shared one seed. The day was later regenerated as part of the five-week history (`docs/decisions.md` §16); history days are checked against their manifests and answer keys before training (`10_gap_risk_model.md`). |
| 2026-10-18 12:56:56 | 2026-10-19 | 40 of 40 |  |
| 2026-10-18 13:38:13 | 2026-10-19 | 40 of 40 |  |
| 2026-10-19 01:28:58 | 2026-10-19 | 43 of 43 |  |
| 2026-10-19 02:35:51 | 2026-10-19 | 43 of 43 |  |

## Business date 2026-10-17: 40 of 40 checks passed

_Checked the earlier version of this day, when every simulated day shared one seed. The day was later regenerated as part of the five-week history (`docs/decisions.md` §16); history days are checked against their manifests and answer keys before training (`10_gap_risk_model.md`)._

| stage | metric | value | expected | passed | note |
|---|---|---|---|---|---|
| raw | files_landed | 23 |  | true |  |
| raw | rows_landed | 6,264,110 |  | true |  |
| bronze | rows_allocations | 96,504 | 96,504 | true | matches the source manifest |
| bronze | rows_deliveries | 385,230 | 385,230 | true | matches the source manifest |
| bronze | rows_depot_master | 7 | 7 | true | matches the source manifest |
| bronze | rows_ingested | 6,264,110 | 6,264,110 | true | matches the source manifest |
| bronze | rows_order_events | 111,283 | 111,283 | true | matches the source manifest |
| bronze | rows_product_master | 6,025 | 6,025 | true | matches the source manifest |
| bronze | rows_stock_counts | 73,820 | 73,820 | true | matches the source manifest |
| bronze | rows_store_master | 900 | 900 | true | matches the source manifest |
| bronze | rows_store_stock | 5,400,000 | 5,400,000 | true | matches the source manifest |
| bronze | rows_supplier_master | 120 | 120 | true | matches the source manifest |
| bronze | rows_waste | 190,221 | 190,221 | true | matches the source manifest |
| silver | duplicates_removed | 3,813 | 3,813 | true | re-sent delivery lines |
| silver | expectation_violations | 520 |  | true | dropped rows plus warnings (over-deliveries are kept and flagged) |
| silver | expectations_evaluated | 38 |  | true | pipeline update e01ac9df-2483-485b-b193-c69c55918ff6 |
| silver | rows_dropped | 120 | 120 | true | malformed delivery lines: no store, bad barcode or negative units |
| gold | answer_key_matches | 205,834 | 205,834 | true | status, low type, root cause, short type and all six quantities, row by row |
| gold | attributed_pct | 98 |  | true | share of gaps and lows with a confirmed root cause |
| gold | exceptions | 205,834 | 205,834 | true |  |
| gold | gaps | 133,765 | 133,765 | true |  |
| gold | hard_constraint_failures | 0 | 0 | true | every gap or low has a root cause, healthy shelves have none, every row is mastered |
| gold | lows | 72,069 | 72,069 | true |  |
| gold | multi_evidence_exceptions | 59,992 |  | true | exceptions where the cascade had to choose between several kinds of evidence |
| gold | owned_product_locations | 4,908,000 | 4,908,000 | true |  |
| gold | product_locations | 5,400,000 | 5,400,000 | true |  |
| gold | reason_investigate | 4,085 | 4,085 | true |  |
| gold | reason_known_gap | 62,251 | 62,251 | true |  |
| gold | reason_order_delivery_block | 24,491 | 24,491 | true |  |
| gold | reason_scarcity | 16,573 | 16,573 | true |  |
| gold | reason_stockfile_adjustment | 16,297 | 16,297 | true |  |
| gold | reason_supplier_short | 40,711 | 40,711 | true |  |
| gold | reason_under_forecast | 30,989 | 30,989 | true |  |
| gold | reason_waste | 10,437 | 10,437 | true |  |
| gold | sales_lows | 36,099 | 36,099 | true |  |
| gold | space_lows | 35,970 | 35,970 | true |  |
| governance | availability_pct | 97.52 |  | true | from the governed metric view |
| governance | metric_view_gap_rate_pct | 2.48 | 2.48 | true | metric view agrees with the table |
| lakebase | synced_exceptions | 205,834 | 205,834 | true |  |
| lakebase | synced_rows | 5,400,000 | 5,400,000 | true | Lakebase copy for Shelf Scan |

## Business date 2026-10-18: 36 of 40 checks passed

_Checked the earlier version of this day, when every simulated day shared one seed. The day was later regenerated as part of the five-week history (`docs/decisions.md` §16); history days are checked against their manifests and answer keys before training (`10_gap_risk_model.md`)._

| stage | metric | value | expected | passed | note |
|---|---|---|---|---|---|
| raw | files_landed | 23 |  | true |  |
| raw | rows_landed | 6,264,242 |  | true |  |
| bronze | rows_allocations | 96,504 | 96,497 | false | matches the source manifest |
| bronze | rows_deliveries | 385,230 | 385,230 | true | matches the source manifest |
| bronze | rows_depot_master | 7 | 7 | true | matches the source manifest |
| bronze | rows_ingested | 6,264,110 | 6,264,242 | false | matches the source manifest |
| bronze | rows_order_events | 111,283 | 111,283 | true | matches the source manifest |
| bronze | rows_product_master | 6,025 | 6,025 | true | matches the source manifest |
| bronze | rows_stock_counts | 73,820 | 73,820 | true | matches the source manifest |
| bronze | rows_store_master | 900 | 900 | true | matches the source manifest |
| bronze | rows_store_stock | 5,400,000 | 5,400,000 | true | matches the source manifest |
| bronze | rows_supplier_master | 120 | 120 | true | matches the source manifest |
| bronze | rows_waste | 190,221 | 190,360 | false | matches the source manifest |
| silver | duplicates_removed | 3,813 | 3,813 | true | re-sent delivery lines |
| silver | expectation_violations | 1,040 |  | true | dropped rows plus warnings (over-deliveries are kept and flagged) |
| silver | expectations_evaluated | 38 |  | true | pipeline update 8af7a2ee-c712-49c6-a255-4362b959fe9d |
| silver | rows_dropped | 120 | 120 | true | malformed delivery lines: no store, bad barcode or negative units |
| gold | answer_key_matches | 45,800 | 205,834 | false | status, low type, root cause, short type and all six quantities, row by row |
| gold | attributed_pct | 98 |  | true | share of gaps and lows with a confirmed root cause |
| gold | exceptions | 205,834 | 205,834 | true |  |
| gold | gaps | 133,765 | 133,765 | true |  |
| gold | hard_constraint_failures | 0 | 0 | true | every gap or low has a root cause, healthy shelves have none, every row is mastered |
| gold | lows | 72,069 | 72,069 | true |  |
| gold | multi_evidence_exceptions | 59,992 |  | true | exceptions where the cascade had to choose between several kinds of evidence |
| gold | owned_product_locations | 4,908,000 | 4,908,000 | true |  |
| gold | product_locations | 5,400,000 | 5,400,000 | true |  |
| gold | reason_investigate | 4,085 | 4,085 | true |  |
| gold | reason_known_gap | 62,251 | 62,251 | true |  |
| gold | reason_order_delivery_block | 24,491 | 24,491 | true |  |
| gold | reason_scarcity | 16,573 | 16,573 | true |  |
| gold | reason_stockfile_adjustment | 16,297 | 16,297 | true |  |
| gold | reason_supplier_short | 40,711 | 40,711 | true |  |
| gold | reason_under_forecast | 30,989 | 30,989 | true |  |
| gold | reason_waste | 10,437 | 10,437 | true |  |
| gold | sales_lows | 36,099 | 36,099 | true |  |
| gold | space_lows | 35,970 | 35,970 | true |  |
| governance | availability_pct | 97.52 |  | true | from the governed metric view |
| governance | metric_view_gap_rate_pct | 2.48 | 2.48 | true | metric view agrees with the table |
| lakebase | synced_exceptions | 205,834 | 205,834 | true |  |
| lakebase | synced_rows | 5,400,000 | 5,400,000 | true | Lakebase copy for Shelf Scan |

## Business date 2026-10-19: 43 of 43 checks passed

| stage | metric | value | expected | passed | note |
|---|---|---|---|---|---|
| raw | files_landed | 23 |  | true |  |
| raw | rows_landed | 6,264,018 |  | true |  |
| bronze | rows_allocations | 96,510 | 96,510 | true | matches the source manifest |
| bronze | rows_deliveries | 385,230 | 385,230 | true | matches the source manifest |
| bronze | rows_depot_master | 7 | 7 | true | matches the source manifest |
| bronze | rows_ingested | 6,264,018 | 6,264,018 | true | matches the source manifest |
| bronze | rows_order_events | 111,283 | 111,283 | true | matches the source manifest |
| bronze | rows_product_master | 6,025 | 6,025 | true | matches the source manifest |
| bronze | rows_stock_counts | 73,820 | 73,820 | true | matches the source manifest |
| bronze | rows_store_master | 900 | 900 | true | matches the source manifest |
| bronze | rows_store_stock | 5,400,000 | 5,400,000 | true | matches the source manifest |
| bronze | rows_supplier_master | 120 | 120 | true | matches the source manifest |
| bronze | rows_waste | 190,123 | 190,123 | true | matches the source manifest |
| silver | duplicates_removed | 3,813 | 3,813 | true | re-sent delivery lines |
| silver | expectation_violations | 18,720 |  | true | dropped rows plus warnings (over-deliveries are kept and flagged) |
| silver | expectations_evaluated | 46 |  | true | pipeline update 4af604b5-aa13-4b1d-80af-676c4a46ed2e |
| silver | rows_dropped | 120 | 120 | true | malformed delivery lines: no store, bad barcode or negative units |
| gold | answer_key_matches | 205,834 | 205,834 | true | status, low type, root cause, short type and all six quantities, row by row |
| gold | attributed_pct | 98 |  | true | share of gaps and lows with a confirmed root cause |
| gold | exceptions | 205,834 | 205,834 | true |  |
| gold | gaps | 133,765 | 133,765 | true |  |
| gold | hard_constraint_failures | 0 | 0 | true | every gap or low has a root cause, healthy shelves have none, every row is mastered |
| gold | lows | 72,069 | 72,069 | true |  |
| gold | multi_evidence_exceptions | 59,993 |  | true | exceptions where the cascade had to choose between several kinds of evidence |
| gold | owned_product_locations | 4,908,000 | 4,908,000 | true |  |
| gold | product_locations | 5,400,000 | 5,400,000 | true |  |
| gold | reason_investigate | 4,085 | 4,085 | true |  |
| gold | reason_known_gap | 62,251 | 62,251 | true |  |
| gold | reason_order_delivery_block | 24,491 | 24,491 | true |  |
| gold | reason_scarcity | 16,573 | 16,573 | true |  |
| gold | reason_stockfile_adjustment | 16,297 | 16,297 | true |  |
| gold | reason_supplier_short | 40,711 | 40,711 | true |  |
| gold | reason_under_forecast | 30,989 | 30,989 | true |  |
| gold | reason_waste | 10,437 | 10,437 | true |  |
| gold | sales_lows | 36,099 | 36,099 | true |  |
| gold | space_lows | 35,970 | 35,970 | true |  |
| governance | availability_pct | 97.52 |  | true | from the governed metric view |
| governance | metric_view_gap_rate_pct | 2.48 | 2.48 | true | metric view agrees with the table |
| lakebase | synced_exceptions | 205,834 | 205,834 | true |  |
| lakebase | synced_rows | 5,400,000 | 5,400,000 | true | Lakebase copy for Shelf Scan |
| ml | feature_gaps_match_gold | 93,319 | 93,319 | true | unplanned gaps in the features agree with gold |
| ml | feature_history_days | 36 |  | true | days of features; scoring needs the last 7 |
| ml | feature_rows | 5,400,000 | 5,400,000 | true | one row of gap-risk features per product-location |

