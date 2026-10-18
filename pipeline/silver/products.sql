-- Silver: Current product master: the latest record per line, so a price change re-issued by master data wins.
CREATE OR REFRESH MATERIALIZED VIEW silver.products (
  CONSTRAINT valid_upc EXPECT (upc RLIKE '^[0-9]{13}$') ON VIOLATION DROP ROW,
  CONSTRAINT positive_price EXPECT (unit_price_gbp > 0),
  CONSTRAINT has_supplier EXPECT (supplier_id IS NOT NULL)
)
COMMENT 'Current product master: the latest record per line, so a price change re-issued by master data wins. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT upc, product_name, category, department, product_group, temperature_cluster, supplier_id, unit_price_gbp, shelf_life_days, case_size, effective_date
FROM bronze.product_master
QUALIFY ROW_NUMBER() OVER (PARTITION BY upc ORDER BY effective_date DESC, _ingested_at DESC) = 1;
