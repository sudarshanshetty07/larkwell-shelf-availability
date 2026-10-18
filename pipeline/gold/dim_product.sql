-- Gold: product range with supplier, price and shelf life.
CREATE OR REFRESH MATERIALIZED VIEW gold.dim_product (
  CONSTRAINT product_has_supplier EXPECT (supplier IS NOT NULL) ON VIOLATION FAIL UPDATE
)
COMMENT 'Larkwell Foods product range (fictitious): cluster > department (super_group) > category > product group > line, with supplier, price and shelf life.'
TBLPROPERTIES ('quality' = 'gold')
AS SELECT
  p.upc,
  p.product_name AS product,
  p.temperature_cluster AS cluster,
  p.department AS super_group,
  p.category,
  p.product_group,
  p.supplier_id,
  s.supplier_name AS supplier,
  p.unit_price_gbp,
  p.shelf_life_days,
  p.case_size
FROM silver.products p
LEFT JOIN silver.suppliers s ON s.supplier_id = p.supplier_id;
