-- Bronze: Daily store stock and sales extract: one row per store x line (gzip CSV, one file per area).
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.store_stock
COMMENT 'Daily store stock and sales extract: one row per store x line (gzip CSV, one file per area), exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/store_stock/',
  format => 'csv',
  header => true,
  schemaHints => 'business_date DATE, store_id STRING, upc STRING, range_status STRING, on_hand_units INT, presentation_min_units INT, shelf_capacity_units INT, forecast_units INT, sales_units INT'
);
