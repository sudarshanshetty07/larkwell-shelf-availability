-- Silver: Latest status of every store order that hit a block. Released orders are no longer blocked.
CREATE OR REFRESH MATERIALIZED VIEW silver.order_status (
  CONSTRAINT valid_store_id EXPECT (store_id IS NOT NULL AND store_id RLIKE '^S[0-9]{4}$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_upc EXPECT (upc IS NOT NULL AND upc RLIKE '^[0-9]{13}$') ON VIOLATION DROP ROW,
  CONSTRAINT known_status EXPECT (latest_status IN ('BLOCKED', 'CANCELLED', 'RELEASED')) ON VIOLATION DROP ROW
)
COMMENT 'Latest status of every store order that hit a block. Released orders are no longer blocked. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT order_id, store_id, upc, status AS latest_status, event_ts AS status_at, business_date
FROM bronze.order_events
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY event_ts DESC, event_id DESC) = 1;
