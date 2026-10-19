# Lakeflow Spark Declarative Pipeline runs

_Generated 2026-10-19 08:08 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

Pipeline `larkwell_osa_availability`: serverless=True, development=False, channel=CURRENT, catalog `larkwell_osa`, 1 library glob (27 SQL files: 10 bronze, 11 silver, 5 gold, 1 ml). Managed by the bundle in `resources/availability_pipeline.pipeline.yml`.

## Recent updates

| update | state | triggered by | full refresh | validate only | started (UTC) |
|---|---|---|---|---|---|
| 4af604b5-aa13-4b1d-80af-676c4a46ed2e | COMPLETED | JOB_TASK | False | False | 2026-10-19 02:33 |
| 3fbd0619-fc55-4203-abfe-99d64afca652 | COMPLETED | JOB_TASK | True | False | 2026-10-19 01:17 |
| a44b1835-b06a-4ce4-b676-3b9d3d469fe2 | COMPLETED | JOB_TASK | False | False | 2026-10-18 12:50 |
| 8af7a2ee-c712-49c6-a255-4362b959fe9d | COMPLETED | JOB_TASK | False | False | 2026-10-18 12:39 |
| b0e432df-7645-4e86-b243-16218386acd6 | COMPLETED | JOB_TASK | False | False | 2026-10-18 12:04 |
| 2ceb3b6f-9aa3-46cc-98d7-edab816197a1 | COMPLETED | JOB_TASK | False | False | 2026-10-18 11:54 |
| e01ac9df-2483-485b-b193-c69c55918ff6 | COMPLETED | API_CALL | True | False | 2026-10-18 11:08 |
| b0aca80a-e6e2-49a5-b7ab-58170c784e35 | COMPLETED | API_CALL | False | False | 2026-10-18 10:50 |

## Incremental ingestion: rows each bronze table read, in the last three updates

Auto Loader reads only files it hasn't seen. Streaming tables report rows as they run, so these are summed from the running progress events. Oldest first: the last daily run before the history existed found no new files; the history backfill's full refresh re-read every file of all 36 trading days; and the daily run after it found no new files and read nothing, while silver, gold and the model's features were recomputed. (Day two of the original build had read just day two's files.)

| bronze table | update a44b1835 (10-18 12:50) | update 3fbd0619 (10-19 01:17) | update 4af604b5 (10-19 02:33) |
|---|---|---|---|
| allocations | 96,510 | 2,446,731 | 0 |
| deliveries | 385,230 | 13,781,526 | 0 |
| depot_master | 7 | 252 | 0 |
| order_events | 111,283 | 3,790,968 | 0 |
| product_master | 6,025 | 216,150 | 0 |
| stock_counts | 73,820 | 2,591,719 | 0 |
| store_master | 900 | 32,400 | 0 |
| store_stock | 5,400,000 | 194,400,000 | 0 |
| supplier_master | 120 | 4,320 | 0 |
| waste | 190,123 | 5,470,370 | 0 |

## Rows written by silver and gold in the latest update (4af604b5-aa13-4b1d-80af-676c4a46ed2e)

| dataset | rows_written |
|---|---|
| larkwell_osa.gold.dim_depot | 7 |
| larkwell_osa.gold.dim_product | 6,000 |
| larkwell_osa.gold.dim_store | 900 |
| larkwell_osa.gold.dim_supplier | 120 |
| larkwell_osa.gold.product_location_status | 5,400,000 |
| larkwell_osa.ml.gap_risk_features | 194,400,000 |
| larkwell_osa.silver.allocations | 2,446,731 |
| larkwell_osa.silver.delivery_lines | 13,640,795 |
| larkwell_osa.silver.depots | 7 |
| larkwell_osa.silver.order_status | 2,757,349 |
| larkwell_osa.silver.products | 6,000 |
| larkwell_osa.silver.stock_counts | 2,591,719 |
| larkwell_osa.silver.store_stock | 5,400,000 |
| larkwell_osa.silver.store_stock_history | 194,400,000 |
| larkwell_osa.silver.stores | 900 |
| larkwell_osa.silver.suppliers | 120 |
| larkwell_osa.silver.waste_events | 5,470,370 |

## Data-quality expectations in the latest update

Silver drops malformed delivery lines (no store, bad barcode, negative units) and warns on over-deliveries. Gold's three constraints fail the update if violated.

| dataset | expectation | passed | failed |
|---|---|---|---|
| larkwell_osa.gold.dim_product | product_has_supplier | 6,000 | 0 |
| larkwell_osa.gold.dim_store | store_has_depot | 900 | 0 |
| larkwell_osa.gold.product_location_status | exception_has_root_cause | 5,400,000 | 0 |
| larkwell_osa.gold.product_location_status | healthy_shelf_has_no_root_cause | 5,400,000 | 0 |
| larkwell_osa.gold.product_location_status | product_location_is_mastered | 5,400,000 | 0 |
| larkwell_osa.ml.gap_risk_features | cover_is_valid | 194,400,000 | 0 |
| larkwell_osa.ml.gap_risk_features | line_is_mastered | 194,400,000 | 0 |
| larkwell_osa.ml.gap_risk_features | rates_are_shares | 194,400,000 | 0 |
| larkwell_osa.silver.allocations | non_negative_units | 2,446,731 | 0 |
| larkwell_osa.silver.allocations | not_over_allocated | 2,446,731 | 0 |
| larkwell_osa.silver.allocations | valid_store_id | 2,446,731 | 0 |
| larkwell_osa.silver.allocations | valid_upc | 2,446,731 | 0 |
| larkwell_osa.silver.delivery_lines | non_negative_units | 13,643,675 | 1,440 |
| larkwell_osa.silver.delivery_lines | not_over_delivered | 13,630,715 | 14,400 |
| larkwell_osa.silver.delivery_lines | valid_store_id | 13,643,675 | 1,440 |
| larkwell_osa.silver.delivery_lines | valid_upc | 13,643,675 | 1,440 |
| larkwell_osa.silver.depots | valid_depot_id | 7 | 0 |
| larkwell_osa.silver.order_status | known_status | 2,757,349 | 0 |
| larkwell_osa.silver.order_status | valid_store_id | 2,757,349 | 0 |
| larkwell_osa.silver.order_status | valid_upc | 2,757,349 | 0 |
| larkwell_osa.silver.products | has_supplier | 6,000 | 0 |
| larkwell_osa.silver.products | positive_price | 6,000 | 0 |
| larkwell_osa.silver.products | valid_upc | 6,000 | 0 |
| larkwell_osa.silver.stock_counts | known_reason | 2,591,719 | 0 |
| larkwell_osa.silver.stock_counts | non_zero_adjustment | 2,591,719 | 0 |
| larkwell_osa.silver.stock_counts | valid_store_id | 2,591,719 | 0 |
| larkwell_osa.silver.stock_counts | valid_upc | 2,591,719 | 0 |
| larkwell_osa.silver.store_stock | capacity_covers_minimum | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | known_range_status | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | non_negative_stock | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | positive_forecast | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | valid_store_id | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | valid_upc | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock_history | known_range_status | 194,400,000 | 0 |
| larkwell_osa.silver.store_stock_history | non_negative_stock | 194,400,000 | 0 |
| larkwell_osa.silver.store_stock_history | positive_forecast | 194,400,000 | 0 |
| larkwell_osa.silver.store_stock_history | valid_store_id | 194,400,000 | 0 |
| larkwell_osa.silver.store_stock_history | valid_upc | 194,400,000 | 0 |
| larkwell_osa.silver.stores | has_depot | 900 | 0 |
| larkwell_osa.silver.stores | known_format | 900 | 0 |
| larkwell_osa.silver.stores | known_ownership | 900 | 0 |
| larkwell_osa.silver.stores | valid_store_id | 900 | 0 |
| larkwell_osa.silver.suppliers | valid_supplier_id | 120 | 0 |
| larkwell_osa.silver.waste_events | positive_waste | 5,470,370 | 0 |
| larkwell_osa.silver.waste_events | valid_store_id | 5,470,370 | 0 |
| larkwell_osa.silver.waste_events | valid_upc | 5,470,370 | 0 |

## Rows per layer now

| dataset | rows |
|---|---|
| silver.store_stock (latest per product-location) | 5,400,000 |
| silver.store_stock_history (every day, last six weeks) | 194,400,000 |
| silver.delivery_lines | 13,640,795 |
| bronze.store_stock | 194,400,000 |
| bronze.deliveries | 13,781,526 |
| gold.product_location_status | 5,400,000 |
| ml.gap_risk_features (one row per product-location per day) | 194,400,000 |
