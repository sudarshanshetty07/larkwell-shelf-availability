-- Silver (de-duplicated within each business day, because source IDs can restart daily): Waste write-offs recorded in store.
CREATE OR REFRESH MATERIALIZED VIEW silver.waste_events (
  CONSTRAINT valid_store_id EXPECT (store_id IS NOT NULL AND store_id RLIKE '^S[0-9]{4}$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_upc EXPECT (upc IS NOT NULL AND upc RLIKE '^[0-9]{13}$') ON VIOLATION DROP ROW,
  CONSTRAINT positive_waste EXPECT (waste_units > 0) ON VIOLATION DROP ROW
)
COMMENT 'Waste write-offs recorded in store. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT waste_id, business_date, store_id, upc, waste_units, waste_reason, recorded_at
FROM bronze.waste
QUALIFY ROW_NUMBER() OVER (PARTITION BY business_date, waste_id ORDER BY _ingested_at) = 1;
