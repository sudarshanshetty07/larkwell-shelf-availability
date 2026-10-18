-- Silver (de-duplicated within each business day, because source IDs can restart daily): Delivery lines with re-sent duplicates removed (one row per delivery line id) and malformed lines dropped.
CREATE OR REFRESH MATERIALIZED VIEW silver.delivery_lines (
  CONSTRAINT valid_store_id EXPECT (store_id IS NOT NULL AND store_id RLIKE '^S[0-9]{4}$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_upc EXPECT (upc IS NOT NULL AND upc RLIKE '^[0-9]{13}$') ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_units EXPECT (ordered_units >= 0 AND delivered_units >= 0) ON VIOLATION DROP ROW,
  CONSTRAINT not_over_delivered EXPECT (delivered_units <= ordered_units)
)
COMMENT 'Delivery lines with re-sent duplicates removed (one row per delivery line id) and malformed lines dropped. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT delivery_line_id, business_date, store_id, upc, depot_id, supplier_id, ordered_units, delivered_units, short_reason, delivered_at
FROM bronze.deliveries
QUALIFY ROW_NUMBER() OVER (PARTITION BY business_date, delivery_line_id ORDER BY _ingested_at) = 1;
