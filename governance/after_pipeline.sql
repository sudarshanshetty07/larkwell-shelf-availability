-- Run after the first pipeline update (the tables must exist): tags on pipeline tables and the access-control table.
ALTER MATERIALIZED VIEW larkwell_osa.gold.product_location_status SET TAGS ('data_classification' = 'internal', 'domain' = 'retail');
ALTER MATERIALIZED VIEW larkwell_osa.gold.dim_store SET TAGS ('data_classification' = 'internal', 'domain' = 'retail');
ALTER MATERIALIZED VIEW larkwell_osa.gold.dim_product SET TAGS ('data_classification' = 'internal', 'domain' = 'retail');
ALTER MATERIALIZED VIEW larkwell_osa.gold.dim_supplier SET TAGS ('data_classification' = 'internal', 'domain' = 'retail');
ALTER MATERIALIZED VIEW larkwell_osa.gold.dim_depot SET TAGS ('data_classification' = 'internal', 'domain' = 'retail');
ALTER STREAMING TABLE larkwell_osa.bronze.store_stock SET TAGS ('data_classification' = 'internal', 'domain' = 'ingestion');
ALTER MATERIALIZED VIEW larkwell_osa.ml.gap_risk_features SET TAGS ('data_classification' = 'internal', 'domain' = 'retail');
CREATE TABLE IF NOT EXISTS larkwell_osa.ops.app_user_roles (
  email STRING NOT NULL COMMENT 'User sign-in email (personal data)',
  persona STRING NOT NULL COMMENT 'App persona: support_centre (head office), support_centre_store, support_centre_category, retail_regional or retail_store_manager',
  store_filter STRING COMMENT 'Store a store manager is limited to (blank for none)',
  division_filter STRING COMMENT 'Division a regional manager is limited to (blank for none)',
  is_admin BOOLEAN NOT NULL COMMENT 'Admins see every persona and scope')
  COMMENT 'Who can use the Shelf Availability app and what they see. The app returns 403 to anyone not listed here.';
ALTER TABLE larkwell_osa.ops.app_user_roles ALTER COLUMN email SET TAGS ('data_classification' = 'pii');
ALTER TABLE larkwell_osa.ops.app_user_roles SET TAGS ('data_classification' = 'confidential');
MERGE INTO larkwell_osa.ops.app_user_roles t
USING (SELECT * FROM VALUES
  ('regional.demo@larkwell.example', 'retail_regional', '', 'South', false),
  ('category.demo@larkwell.example', 'support_centre_category', '', '', false),
  ('store.demo@larkwell.example', 'retail_store_manager', 'Covent Garden', '', false)
  AS v(email, persona, store_filter, division_filter, is_admin)) s
ON t.email = s.email
WHEN NOT MATCHED THEN INSERT *;
-- Then add yourself as an admin:  INSERT INTO larkwell_osa.ops.app_user_roles VALUES ('<you>', 'support_centre', '', '', true);
