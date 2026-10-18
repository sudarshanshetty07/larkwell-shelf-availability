-- Bronze: Distribution centre master records.
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.depot_master
COMMENT 'Distribution centre master records, exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/depot_master/',
  format => 'csv',
  header => true,
  schemaHints => 'depot_id STRING, depot_name STRING, region_served STRING, effective_date DATE'
);
