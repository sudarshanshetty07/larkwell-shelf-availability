# Raw feeds landed by the simulated source systems

_Generated 2026-10-18 14:18 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

The generator (`data/01_land_raw_feeds.py`) plays the source systems and lands one folder per feed per trading day in the Unity Catalog volume `raw.landing`. Each day also gets a manifest, which the daily checks reconcile against.

## Business date 2026-10-17

| feed | files | rows | example file |
|---|---|---|---|
| store_master | 1 | 900 | store_master_2026-10-17.csv |
| product_master | 1 | 6,025 | product_master_2026-10-17.csv |
| supplier_master | 1 | 120 | supplier_master_2026-10-17.csv |
| depot_master | 1 | 7 | depot_master_2026-10-17.csv |
| store_stock | 9 | 5,400,000 | store_stock_2026-10-17_scotland.csv.gz |
| deliveries | 4 | 385,230 | deliveries_2026-10-17_part1.json |
| order_events | 2 | 111,283 | order_events_2026-10-17_part1.json |
| stock_counts | 1 | 73,820 | stock_counts_2026-10-17_part1.json |
| waste | 2 | 190,221 | waste_2026-10-17_part1.json |
| allocations | 1 | 96,504 | allocations_2026-10-17_part1.json |

## Business date 2026-10-18

| feed | files | rows | example file |
|---|---|---|---|
| store_master | 1 | 900 | store_master_2026-10-18.csv |
| product_master | 1 | 6,025 | product_master_2026-10-18.csv |
| supplier_master | 1 | 120 | supplier_master_2026-10-18.csv |
| depot_master | 1 | 7 | depot_master_2026-10-18.csv |
| store_stock | 9 | 5,400,000 | store_stock_2026-10-18_scotland.csv.gz |
| deliveries | 4 | 385,230 | deliveries_2026-10-18_part1.json |
| order_events | 2 | 111,283 | order_events_2026-10-18_part1.json |
| stock_counts | 1 | 73,820 | stock_counts_2026-10-18_part1.json |
| waste | 2 | 190,360 | waste_2026-10-18_part1.json |
| allocations | 1 | 96,497 | allocations_2026-10-18_part1.json |

## Business date 2026-10-19

| feed | files | rows | example file |
|---|---|---|---|
| store_master | 1 | 900 | store_master_2026-10-19.csv |
| product_master | 1 | 6,025 | product_master_2026-10-19.csv |
| supplier_master | 1 | 120 | supplier_master_2026-10-19.csv |
| depot_master | 1 | 7 | depot_master_2026-10-19.csv |
| store_stock | 9 | 5,400,000 | store_stock_2026-10-19_scotland.csv.gz |
| deliveries | 4 | 385,230 | deliveries_2026-10-19_part1.json |
| order_events | 2 | 111,283 | order_events_2026-10-19_part1.json |
| stock_counts | 1 | 73,820 | stock_counts_2026-10-19_part1.json |
| waste | 2 | 190,123 | waste_2026-10-19_part1.json |
| allocations | 1 | 96,510 | allocations_2026-10-19_part1.json |

## Answer key (written alongside, never read by the pipeline)

```json
{
  "product_locations": 5400000,
  "stores": 900,
  "lines": 6000,
  "gaps": 133765,
  "lows": 72069,
  "sales_lows": 36099,
  "space_lows": 35970,
  "owned_product_locations": 4908000,
  "reason_mix": {
    "KNOWN_GAP": 62251,
    "SUPPLIER_SHORT": 40711,
    "UNDER_FORECAST": 30989,
    "ORDER_DELIVERY_BLOCK": 24491,
    "SCARCITY": 16573,
    "STOCKFILE_ADJUSTMENT": 16297,
    "WASTE": 10437,
    "INVESTIGATE": 4085
  },
  "supplier_short_types": {
    "LOGISTICS_DELAY": 10226,
    "DEPOT_SHORT": 10195,
    "RAW_MATERIAL_SHORTAGE": 10183,
    "PRODUCTION_ISSUE": 10107
  },
  "malformed_delivery_lines": 120,
  "duplicate_delivery_lines": 3813,
  "daily_forecast_sales_gbp": 22605591.34
}
```
