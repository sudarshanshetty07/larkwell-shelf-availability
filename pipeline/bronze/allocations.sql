-- Bronze: Supply allocation decisions: market shortages and promotional caps.
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.allocations
COMMENT 'Supply allocation decisions: market shortages and promotional caps, exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/allocations/',
  format => 'json',
  schemaHints => 'allocation_id STRING, business_date DATE, store_id STRING, upc STRING, allocation_reason STRING, requested_units INT, allocated_units INT'
);
