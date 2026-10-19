-- Silver: every trading day's stock and sales position for every product-location, the last six weeks.
-- silver.store_stock keeps only the latest day, for the root-cause rules. The gap-risk model needs the history.
CREATE OR REFRESH MATERIALIZED VIEW silver.store_stock_history (
  CONSTRAINT valid_store_id EXPECT (store_id IS NOT NULL AND store_id RLIKE '^S[0-9]{4}$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_upc EXPECT (upc IS NOT NULL AND upc RLIKE '^[0-9]{13}$') ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_stock EXPECT (on_hand_units >= 0 AND sales_units >= 0) ON VIOLATION DROP ROW,
  CONSTRAINT known_range_status EXPECT (range_status IN ('ACTIVE', 'EXITING')) ON VIOLATION DROP ROW,
  CONSTRAINT positive_forecast EXPECT (forecast_units > 0) ON VIOLATION DROP ROW
)
COMMENT 'Every trading day''s stock and sales position for every product-location over the last six weeks (one row per day x store x line). The history the gap-risk model learns from. Synthetic data: Larkwell Foods is fictitious.'
CLUSTER BY (business_date, store_id)
TBLPROPERTIES ('quality' = 'silver')
AS SELECT business_date, store_id, upc, range_status, on_hand_units, presentation_min_units, shelf_capacity_units, forecast_units, sales_units
FROM bronze.store_stock
WHERE business_date > (SELECT date_sub(MAX(business_date), 42) FROM bronze.store_stock)
QUALIFY ROW_NUMBER() OVER (PARTITION BY business_date, store_id, upc ORDER BY _ingested_at DESC) = 1;
