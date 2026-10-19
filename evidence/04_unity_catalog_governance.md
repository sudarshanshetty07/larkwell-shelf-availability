# Unity Catalog governance

_Generated 2026-10-19 08:08 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

## Governed tags

| level | object | tag_name | tag_value |
|---|---|---|---|
| catalog | larkwell_osa | data_classification | internal |
| catalog | larkwell_osa | domain | retail |
| catalog | larkwell_osa | synthetic_data | true |
| column | ops.app_user_roles.email | data_classification | pii |
| schema | bronze | layer | bronze |
| schema | gold | layer | gold |
| schema | ml | layer | ml |
| schema | ops | layer | ops |
| schema | raw | layer | raw |
| schema | silver | layer | silver |
| table | bronze.store_stock | data_classification | internal |
| table | bronze.store_stock | domain | ingestion |
| table | gold.dim_depot | data_classification | internal |
| table | gold.dim_depot | domain | retail |
| table | gold.dim_product | data_classification | internal |
| table | gold.dim_product | domain | retail |
| table | gold.dim_store | data_classification | internal |
| table | gold.dim_store | domain | retail |
| table | gold.dim_supplier | data_classification | internal |
| table | gold.dim_supplier | domain | retail |
| table | gold.product_location_status | data_classification | internal |
| table | gold.product_location_status | domain | retail |
| table | ml.gap_risk_features | data_classification | internal |
| table | ml.gap_risk_features | domain | retail |
| table | ops.app_user_roles | data_classification | confidential |

## Least privilege for the app

The app reads gold, ops and ml (the gap-risk predictions) only, and can't write to the lakehouse at all: its writes go to Lakebase and come back through Lakehouse Sync.

| object | app service principal privileges |
|---|---|
| CATALOG larkwell_osa | USE CATALOG |
| SCHEMA larkwell_osa.gold | SELECT, USE SCHEMA |
| SCHEMA larkwell_osa.ops | SELECT, USE SCHEMA |
| SCHEMA larkwell_osa.ml | SELECT, USE SCHEMA |
| SCHEMA larkwell_osa.silver | none |
| SCHEMA larkwell_osa.bronze | none |

## Lineage, captured automatically (system.access.table_lineage)

| source | target |
|---|---|
| larkwell_osa.ops.lb_colleague_actions_history | larkwell_osa.gold.colleague_actions |
| larkwell_osa.silver.depots | larkwell_osa.gold.dim_depot |
| larkwell_osa.silver.stores | larkwell_osa.gold.dim_depot |
| larkwell_osa.silver.products | larkwell_osa.gold.dim_product |
| larkwell_osa.silver.suppliers | larkwell_osa.gold.dim_product |
| larkwell_osa.silver.depots | larkwell_osa.gold.dim_store |
| larkwell_osa.silver.stores | larkwell_osa.gold.dim_store |
| larkwell_osa.silver.delivery_lines | larkwell_osa.gold.dim_supplier |
| larkwell_osa.silver.products | larkwell_osa.gold.dim_supplier |
| larkwell_osa.silver.suppliers | larkwell_osa.gold.dim_supplier |
| larkwell_osa.gold.product_location_status | larkwell_osa.gold.mv_availability |
| larkwell_osa.gold.dim_product | larkwell_osa.gold.product_location_status |
| larkwell_osa.gold.dim_store | larkwell_osa.gold.product_location_status |
| larkwell_osa.silver.allocations | larkwell_osa.gold.product_location_status |
| larkwell_osa.silver.delivery_lines | larkwell_osa.gold.product_location_status |
| larkwell_osa.silver.order_status | larkwell_osa.gold.product_location_status |
| larkwell_osa.silver.stock_counts | larkwell_osa.gold.product_location_status |
| larkwell_osa.silver.store_stock | larkwell_osa.gold.product_location_status |
| larkwell_osa.silver.waste_events | larkwell_osa.gold.product_location_status |
| larkwell_osa.ops.lb_scan_log_history | larkwell_osa.gold.shelf_scans |
| larkwell_osa.gold.dim_product | larkwell_osa.ml.gap_risk_features |
| larkwell_osa.gold.dim_store | larkwell_osa.ml.gap_risk_features |
| larkwell_osa.silver.allocations | larkwell_osa.ml.gap_risk_features |
| larkwell_osa.silver.delivery_lines | larkwell_osa.ml.gap_risk_features |
| larkwell_osa.silver.order_status | larkwell_osa.ml.gap_risk_features |
| larkwell_osa.silver.stock_counts | larkwell_osa.ml.gap_risk_features |
| larkwell_osa.silver.store_stock_history | larkwell_osa.ml.gap_risk_features |
| larkwell_osa.silver.waste_events | larkwell_osa.ml.gap_risk_features |
| larkwell_osa.gold.dim_product | larkwell_osa.ml.gap_risk_scores |
| larkwell_osa.gold.dim_store | larkwell_osa.ml.gap_risk_scores |
| larkwell_osa.bronze.allocations | larkwell_osa.silver.allocations |
| larkwell_osa.bronze.deliveries | larkwell_osa.silver.delivery_lines |
| larkwell_osa.bronze.depot_master | larkwell_osa.silver.depots |
| larkwell_osa.bronze.order_events | larkwell_osa.silver.order_status |
| larkwell_osa.bronze.product_master | larkwell_osa.silver.products |
| larkwell_osa.bronze.stock_counts | larkwell_osa.silver.stock_counts |
| larkwell_osa.bronze.store_stock | larkwell_osa.silver.store_stock |
| larkwell_osa.bronze.store_stock | larkwell_osa.silver.store_stock_history |
| larkwell_osa.bronze.store_master | larkwell_osa.silver.stores |
| larkwell_osa.bronze.supplier_master | larkwell_osa.silver.suppliers |
| larkwell_osa.bronze.waste | larkwell_osa.silver.waste_events |

## One definition of every KPI (metric view gold.mv_availability)

| division | availability_pct | gap_rate_pct | attributed_pct | actionable_gaps | actionable_sales_at_risk_gbp |
|---|---|---|---|---|---|
| Central | 97.54 | 2.46 | 97.9 | 9,869 | 126,474 |
| North & Scotland | 97.45 | 2.55 | 98.0 | 40,045 | 500,915 |
| South | 97.59 | 2.41 | 98.0 | 43,405 | 548,283 |
|  | 97.52 | 2.48 | 98.0 | 93,319 | 1,175,671 |
