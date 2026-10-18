-- Bronze: Waste write-offs recorded in store.
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.waste
COMMENT 'Waste write-offs recorded in store, exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/waste/',
  format => 'json',
  schemaHints => 'waste_id STRING, business_date DATE, store_id STRING, upc STRING, waste_units INT, waste_reason STRING, recorded_at TIMESTAMP'
);
