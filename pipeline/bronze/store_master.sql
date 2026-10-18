-- Bronze: Store master records from the master-data system.
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.store_master
COMMENT 'Store master records from the master-data system, exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/store_master/',
  format => 'csv',
  header => true,
  schemaHints => 'store_id STRING, store_name STRING, division STRING, area STRING, store_format STRING, ownership STRING, depot_id STRING, effective_date DATE'
);
