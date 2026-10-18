-- Unity Catalog objects for Larkwell Shelf Availability. Larkwell Foods is fictitious; all data is synthetic.
CREATE CATALOG IF NOT EXISTS larkwell_osa COMMENT 'Larkwell Foods (fictitious UK food retailer): on-shelf availability root-cause data product. Synthetic data only.';
CREATE SCHEMA IF NOT EXISTS larkwell_osa.raw COMMENT 'Landing zone: raw daily extracts exactly as the (simulated) source systems deliver them';
CREATE SCHEMA IF NOT EXISTS larkwell_osa.bronze COMMENT 'Bronze: raw feeds ingested incrementally by Auto Loader, unchanged, with source file and ingest time';
CREATE SCHEMA IF NOT EXISTS larkwell_osa.silver COMMENT 'Silver: typed, de-duplicated, quality-checked feeds (Lakeflow expectations)';
CREATE SCHEMA IF NOT EXISTS larkwell_osa.gold COMMENT 'Gold: one governed status and root cause per product-location, plus dimensions and actions';
CREATE SCHEMA IF NOT EXISTS larkwell_osa.ops COMMENT 'Operations: app access control, AI evaluation results and the Lakebase change history of colleague actions';
CREATE VOLUME IF NOT EXISTS larkwell_osa.raw.landing COMMENT 'Daily raw extracts landed by the source systems (CSV and JSON lines)';
CREATE VOLUME IF NOT EXISTS larkwell_osa.raw.answer_key COMMENT 'Answer key written by the data generator to test the pipeline. The pipeline never reads it.';
-- Governed tags (the workspace's tag policies restrict these values)
ALTER CATALOG larkwell_osa SET TAGS ('data_classification' = 'internal', 'domain' = 'retail', 'synthetic_data' = 'true');
ALTER SCHEMA larkwell_osa.raw SET TAGS ('layer' = 'raw');
ALTER SCHEMA larkwell_osa.bronze SET TAGS ('layer' = 'bronze');
ALTER SCHEMA larkwell_osa.silver SET TAGS ('layer' = 'silver');
ALTER SCHEMA larkwell_osa.gold SET TAGS ('layer' = 'gold');
ALTER SCHEMA larkwell_osa.ops SET TAGS ('layer' = 'ops');
