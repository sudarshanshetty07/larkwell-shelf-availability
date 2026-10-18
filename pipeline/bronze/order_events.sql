-- Bronze: Store order status events: blocks, cancellations and releases.
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.order_events
COMMENT 'Store order status events: blocks, cancellations and releases, exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/order_events/',
  format => 'json',
  schemaHints => 'event_id STRING, order_id STRING, store_id STRING, upc STRING, status STRING, block_reason STRING, event_ts TIMESTAMP, business_date DATE'
);
