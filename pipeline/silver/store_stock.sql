-- Silver: Latest stock and sales position for every product-location.
CREATE OR REFRESH MATERIALIZED VIEW silver.store_stock (
  CONSTRAINT valid_store_id EXPECT (store_id IS NOT NULL AND store_id RLIKE '^S[0-9]{4}$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_upc EXPECT (upc IS NOT NULL AND upc RLIKE '^[0-9]{13}$') ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_stock EXPECT (on_hand_units >= 0 AND sales_units >= 0) ON VIOLATION DROP ROW,
  CONSTRAINT known_range_status EXPECT (range_status IN ('ACTIVE', 'EXITING')) ON VIOLATION DROP ROW,
  CONSTRAINT positive_forecast EXPECT (forecast_units > 0) ON VIOLATION DROP ROW,
  CONSTRAINT capacity_covers_minimum EXPECT (shelf_capacity_units >= presentation_min_units)
)
COMMENT 'Latest stock and sales position for every product-location. Synthetic data: Larkwell Foods is fictitious.'
CLUSTER BY (store_id, upc)
TBLPROPERTIES ('quality' = 'silver')
AS SELECT business_date, store_id, upc, range_status, on_hand_units, presentation_min_units, shelf_capacity_units, forecast_units, sales_units
FROM bronze.store_stock
QUALIFY ROW_NUMBER() OVER (PARTITION BY store_id, upc ORDER BY business_date DESC, _ingested_at DESC) = 1;
