-- Bronze: Product master records (range, price, shelf life, supplier).
-- Ingested incrementally by Auto Loader from the landing volume. Rows are kept exactly as received, plus lineage columns.
CREATE OR REFRESH STREAMING TABLE bronze.product_master
COMMENT 'Product master records (range, price, shelf life, supplier), exactly as received, with source file and ingest time. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/product_master/',
  format => 'csv',
  header => true,
  schemaHints => 'upc STRING, product_name STRING, category STRING, department STRING, product_group STRING, temperature_cluster STRING, supplier_id STRING, unit_price_gbp DOUBLE, shelf_life_days INT, case_size INT, effective_date DATE'
);
