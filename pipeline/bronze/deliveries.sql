-- Bronze: Depot and supplier delivery lines, including re-sent duplicates and malformed records.
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.deliveries
COMMENT 'Depot and supplier delivery lines, including re-sent duplicates and malformed records, exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/deliveries/',
  format => 'json',
  schemaHints => 'delivery_line_id STRING, business_date DATE, store_id STRING, upc STRING, depot_id STRING, supplier_id STRING, ordered_units INT, delivered_units INT, short_reason STRING, delivered_at TIMESTAMP'
);
