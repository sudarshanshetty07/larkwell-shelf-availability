-- Silver (de-duplicated within each business day, because source IDs can restart daily): Stock counts and other stock adjustments. Negative STOCK_COUNT adjustments mean phantom stock.
CREATE OR REFRESH MATERIALIZED VIEW silver.stock_counts (
  CONSTRAINT valid_store_id EXPECT (store_id IS NOT NULL AND store_id RLIKE '^S[0-9]{4}$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_upc EXPECT (upc IS NOT NULL AND upc RLIKE '^[0-9]{13}$') ON VIOLATION DROP ROW,
  CONSTRAINT known_reason EXPECT (adjustment_reason IN ('STOCK_COUNT', 'TRANSFER_OUT')) ON VIOLATION DROP ROW,
  CONSTRAINT non_zero_adjustment EXPECT (adjustment_units <> 0)
)
COMMENT 'Stock counts and other stock adjustments. Negative STOCK_COUNT adjustments mean phantom stock. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT count_id, business_date, store_id, upc, adjustment_reason, adjustment_units, counted_at
FROM bronze.stock_counts
QUALIFY ROW_NUMBER() OVER (PARTITION BY business_date, count_id ORDER BY _ingested_at) = 1;
