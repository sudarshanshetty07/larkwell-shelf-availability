# Lakeflow Spark Declarative Pipeline runs

_Generated 2026-10-18 14:18 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

Pipeline `larkwell_osa_availability`: serverless=True, development=False, channel=CURRENT, catalog `larkwell_osa`, 1 library glob (25 SQL files: 10 bronze, 10 silver, 5 gold). Managed by the bundle in `resources/availability_pipeline.pipeline.yml`.

## Recent updates

| update | state | triggered by | full refresh | started (UTC) |
|---|---|---|---|---|
| a44b1835-b06a-4ce4-b676-3b9d3d469fe2 | COMPLETED | JOB_TASK | False | 2026-10-18 12:50 |
| 8af7a2ee-c712-49c6-a255-4362b959fe9d | COMPLETED | JOB_TASK | False | 2026-10-18 12:39 |
| b0e432df-7645-4e86-b243-16218386acd6 | COMPLETED | JOB_TASK | False | 2026-10-18 12:04 |
| 2ceb3b6f-9aa3-46cc-98d7-edab816197a1 | COMPLETED | JOB_TASK | False | 2026-10-18 11:54 |
| e01ac9df-2483-485b-b193-c69c55918ff6 | COMPLETED | API_CALL | True | 2026-10-18 11:08 |
| b0aca80a-e6e2-49a5-b7ab-58170c784e35 | COMPLETED | API_CALL | False | 2026-10-18 10:50 |

## Incremental ingestion: rows each bronze table read, in the last three updates

Auto Loader reads only files it hasn't seen. Streaming tables report rows as they run, so these are summed from the running progress events. The day-two update read just day two's files. The update after it found no new files and read nothing, while silver and gold were recomputed.

| bronze table | update b0e432df (10-18 12:04) | update 8af7a2ee (10-18 12:39) | update a44b1835 (10-18 12:50) |
|---|---|---|---|
| allocations | 0 | 0 | 96,510 |
| deliveries | 0 | 0 | 385,230 |
| depot_master | 0 | 0 | 7 |
| order_events | 0 | 0 | 111,283 |
| product_master | 0 | 0 | 6,025 |
| stock_counts | 0 | 0 | 73,820 |
| store_master | 0 | 0 | 900 |
| store_stock | 0 | 0 | 5,400,000 |
| supplier_master | 0 | 0 | 120 |
| waste | 0 | 0 | 190,123 |

## Rows written by silver and gold in the latest update (a44b1835-b06a-4ce4-b676-3b9d3d469fe2)

| dataset | rows_written |
|---|---|
| larkwell_osa.gold.dim_depot | 7 |
| larkwell_osa.gold.dim_product | 6,000 |
| larkwell_osa.gold.dim_store | 900 |
| larkwell_osa.gold.dim_supplier | 120 |
| larkwell_osa.gold.product_location_status | 5,400,000 |
| larkwell_osa.silver.allocations | 289,518 |
| larkwell_osa.silver.delivery_lines | 1,143,891 |
| larkwell_osa.silver.depots | 7 |
| larkwell_osa.silver.order_status | 244,269 |
| larkwell_osa.silver.products | 6,000 |
| larkwell_osa.silver.stock_counts | 221,460 |
| larkwell_osa.silver.store_stock | 5,400,000 |
| larkwell_osa.silver.stores | 900 |
| larkwell_osa.silver.suppliers | 120 |
| larkwell_osa.silver.waste_events | 570,565 |

## Data-quality expectations in the latest update

Silver drops malformed delivery lines (no store, bad barcode, negative units) and warns on over-deliveries. Gold's three constraints fail the update if violated.

| dataset | expectation | passed | failed |
|---|---|---|---|
| larkwell_osa.gold.dim_product | product_has_supplier | 6,000 | 0 |
| larkwell_osa.gold.dim_store | store_has_depot | 900 | 0 |
| larkwell_osa.gold.product_location_status | exception_has_root_cause | 5,400,000 | 0 |
| larkwell_osa.gold.product_location_status | healthy_shelf_has_no_root_cause | 5,400,000 | 0 |
| larkwell_osa.gold.product_location_status | product_location_is_mastered | 5,400,000 | 0 |
| larkwell_osa.silver.allocations | non_negative_units | 289,518 | 0 |
| larkwell_osa.silver.allocations | not_over_allocated | 289,518 | 0 |
| larkwell_osa.silver.allocations | valid_store_id | 289,518 | 0 |
| larkwell_osa.silver.allocations | valid_upc | 289,518 | 0 |
| larkwell_osa.silver.delivery_lines | non_negative_units | 1,144,131 | 120 |
| larkwell_osa.silver.delivery_lines | not_over_delivered | 1,143,051 | 1,200 |
| larkwell_osa.silver.delivery_lines | valid_store_id | 1,144,131 | 120 |
| larkwell_osa.silver.delivery_lines | valid_upc | 1,144,131 | 120 |
| larkwell_osa.silver.depots | valid_depot_id | 7 | 0 |
| larkwell_osa.silver.order_status | known_status | 244,269 | 0 |
| larkwell_osa.silver.order_status | valid_store_id | 244,269 | 0 |
| larkwell_osa.silver.order_status | valid_upc | 244,269 | 0 |
| larkwell_osa.silver.products | has_supplier | 6,000 | 0 |
| larkwell_osa.silver.products | positive_price | 6,000 | 0 |
| larkwell_osa.silver.products | valid_upc | 6,000 | 0 |
| larkwell_osa.silver.stock_counts | known_reason | 221,460 | 0 |
| larkwell_osa.silver.stock_counts | non_zero_adjustment | 221,460 | 0 |
| larkwell_osa.silver.stock_counts | valid_store_id | 221,460 | 0 |
| larkwell_osa.silver.stock_counts | valid_upc | 221,460 | 0 |
| larkwell_osa.silver.store_stock | capacity_covers_minimum | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | known_range_status | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | non_negative_stock | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | positive_forecast | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | valid_store_id | 5,400,000 | 0 |
| larkwell_osa.silver.store_stock | valid_upc | 5,400,000 | 0 |
| larkwell_osa.silver.stores | has_depot | 900 | 0 |
| larkwell_osa.silver.stores | known_format | 900 | 0 |
| larkwell_osa.silver.stores | known_ownership | 900 | 0 |
| larkwell_osa.silver.stores | valid_store_id | 900 | 0 |
| larkwell_osa.silver.suppliers | valid_supplier_id | 120 | 0 |
| larkwell_osa.silver.waste_events | positive_waste | 570,565 | 0 |
| larkwell_osa.silver.waste_events | valid_store_id | 570,565 | 0 |
| larkwell_osa.silver.waste_events | valid_upc | 570,565 | 0 |

## Rows per layer now

| dataset | rows |
|---|---|
| silver.store_stock (latest per product-location) | 5,400,000 |
| silver.delivery_lines | 1,143,891 |
| bronze.store_stock | 16,200,000 |
| bronze.deliveries | 1,155,690 |
| gold.product_location_status | 5,400,000 |
