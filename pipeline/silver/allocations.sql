-- Silver (de-duplicated within each business day, because source IDs can restart daily): Supply allocations. A MARKET_SHORTAGE allocation below the request is a scarcity cut.
CREATE OR REFRESH MATERIALIZED VIEW silver.allocations (
  CONSTRAINT valid_store_id EXPECT (store_id IS NOT NULL AND store_id RLIKE '^S[0-9]{4}$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_upc EXPECT (upc IS NOT NULL AND upc RLIKE '^[0-9]{13}$') ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_units EXPECT (requested_units >= 0 AND allocated_units >= 0) ON VIOLATION DROP ROW,
  CONSTRAINT not_over_allocated EXPECT (allocated_units <= requested_units)
)
COMMENT 'Supply allocations. A MARKET_SHORTAGE allocation below the request is a scarcity cut. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT allocation_id, business_date, store_id, upc, allocation_reason, requested_units, allocated_units
FROM bronze.allocations
QUALIFY ROW_NUMBER() OVER (PARTITION BY business_date, allocation_id ORDER BY _ingested_at) = 1;
