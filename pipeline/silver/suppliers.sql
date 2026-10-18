-- Silver: Current supplier master.
CREATE OR REFRESH MATERIALIZED VIEW silver.suppliers (
  CONSTRAINT valid_supplier_id EXPECT (supplier_id RLIKE '^SUP[0-9]{3}$') ON VIOLATION DROP ROW
)
COMMENT 'Current supplier master. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT supplier_id, supplier_name, category_specialism, contracted_service_level_pct, effective_date
FROM bronze.supplier_master
QUALIFY ROW_NUMBER() OVER (PARTITION BY supplier_id ORDER BY effective_date DESC, _ingested_at DESC) = 1;
