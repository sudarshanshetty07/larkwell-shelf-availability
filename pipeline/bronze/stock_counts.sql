-- Bronze: Handheld stock counts and other stock adjustments.
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.stock_counts
COMMENT 'Handheld stock counts and other stock adjustments, exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/stock_counts/',
  format => 'json',
  schemaHints => 'count_id STRING, business_date DATE, store_id STRING, upc STRING, adjustment_reason STRING, adjustment_units INT, counted_at TIMESTAMP'
);
