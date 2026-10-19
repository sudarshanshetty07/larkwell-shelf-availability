# Raw feeds landed by the simulated source systems

_Generated 2026-10-19 08:08 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

The generator (`data/01_land_raw_feeds.py`) plays the source systems and lands one folder per feed per trading day in the Unity Catalog volume `raw.landing`. Each day also gets a manifest, which the daily checks reconcile against, and an answer key that the pipeline never reads.

**The anchor day, 2026-10-19, is pinned:** its headline counts are exact, so the business case always shows the same numbers, and the generator reproduces it byte for byte. Every other day is the anchor rolled back (or forward) one day at a time: each shelf's trouble carries over, suppliers, depots and stores have good and bad spells, near-misses leave warning signs, and volumes follow the week. That history is what the gap-risk model learns from (`10_gap_risk_model.md`).

## Every trading day landed

| d | day | days_from_anchor | files | rows | gaps | lows |
|---|---|---|---|---|---|---|
| 2026-09-14 | Mon | -35 | 23 | 6,197,368 | 131,115 | 70,639 |
| 2026-09-15 | Tue | -34 | 23 | 6,191,764 | 129,669 | 69,861 |
| 2026-09-16 | Wed | -33 | 23 | 6,175,187 | 120,893 | 65,135 |
| 2026-09-17 | Thu | -32 | 23 | 6,175,474 | 122,462 | 65,991 |
| 2026-09-18 | Fri | -31 | 23 | 6,182,494 | 125,654 | 67,711 |
| 2026-09-19 | Sat | -30 | 23 | 6,180,501 | 128,227 | 69,114 |
| 2026-09-20 | Sun | -29 | 23 | 6,193,826 | 133,677 | 72,049 |
| 2026-09-21 | Mon | -28 | 23 | 6,205,975 | 134,200 | 72,304 |
| 2026-09-22 | Tue | -27 | 23 | 6,184,390 | 125,630 | 67,690 |
| 2026-09-23 | Wed | -26 | 23 | 6,179,047 | 123,435 | 66,507 |
| 2026-09-24 | Thu | -25 | 23 | 6,172,102 | 121,543 | 65,492 |
| 2026-09-25 | Fri | -24 | 23 | 6,177,116 | 123,331 | 66,462 |
| 2026-09-26 | Sat | -23 | 23 | 6,184,919 | 130,011 | 70,077 |
| 2026-09-27 | Sun | -22 | 23 | 6,188,725 | 129,487 | 69,777 |
| 2026-09-28 | Mon | -21 | 23 | 6,201,355 | 133,641 | 72,006 |
| 2026-09-29 | Tue | -20 | 23 | 6,185,705 | 125,413 | 67,568 |
| 2026-09-30 | Wed | -19 | 23 | 6,176,355 | 123,104 | 66,328 |
| 2026-10-01 | Thu | -18 | 23 | 6,171,442 | 120,037 | 64,685 |
| 2026-10-02 | Fri | -17 | 23 | 6,175,735 | 124,000 | 66,826 |
| 2026-10-03 | Sat | -16 | 23 | 6,182,616 | 127,204 | 68,563 |
| 2026-10-04 | Sun | -15 | 23 | 6,188,030 | 129,590 | 69,833 |
| 2026-10-05 | Mon | -14 | 23 | 6,204,508 | 133,921 | 72,146 |
| 2026-10-06 | Tue | -13 | 23 | 6,187,771 | 128,960 | 69,485 |
| 2026-10-07 | Wed | -12 | 23 | 6,173,478 | 120,107 | 64,718 |
| 2026-10-08 | Thu | -11 | 23 | 6,175,328 | 122,257 | 65,883 |
| 2026-10-09 | Fri | -10 | 23 | 6,179,355 | 124,105 | 66,893 |
| 2026-10-10 | Sat | -9 | 23 | 6,182,894 | 127,446 | 68,694 |
| 2026-10-11 | Sun | -8 | 23 | 6,196,832 | 135,096 | 72,808 |
| 2026-10-12 | Mon | -7 | 23 | 6,206,387 | 136,263 | 73,417 |
| 2026-10-13 | Tue | -6 | 23 | 6,192,972 | 129,519 | 69,779 |
| 2026-10-14 | Wed | -5 | 23 | 6,174,077 | 120,564 | 64,959 |
| 2026-10-15 | Thu | -4 | 23 | 6,172,652 | 122,061 | 65,775 |
| 2026-10-16 | Fri | -3 | 23 | 6,177,604 | 123,630 | 66,618 |
| 2026-10-17 | Sat | -2 | 23 | 6,182,400 | 127,109 | 68,503 |
| 2026-10-18 | Sun | -1 | 23 | 6,194,034 | 131,299 | 70,762 |
| 2026-10-19 | Mon | 0 | 23 | 6,264,018 | 133,765 | 72,069 |

## The anchor day, 2026-10-19, feed by feed

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

## The anchor day's answer key (written alongside, never read by the pipeline)

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
