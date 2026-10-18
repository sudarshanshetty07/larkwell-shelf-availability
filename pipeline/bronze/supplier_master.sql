-- Bronze: Supplier master records with contracted service levels.
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.supplier_master
COMMENT 'Supplier master records with contracted service levels, exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/supplier_master/',
  format => 'csv',
  header => true,
  schemaHints => 'supplier_id STRING, supplier_name STRING, category_specialism STRING, contracted_service_level_pct DOUBLE, effective_date DATE'
);
