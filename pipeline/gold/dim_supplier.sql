-- Gold: suppliers with the latest day's delivery performance, measured from the deliveries feed.
CREATE OR REFRESH MATERIALIZED VIEW gold.dim_supplier
COMMENT 'Larkwell Foods suppliers (fictitious) with delivery performance: lines delivered, units short and fill rate against the contracted service level.'
TBLPROPERTIES ('quality' = 'gold')
AS WITH perf AS (
  SELECT
    supplier_id,
    COUNT(*) AS delivery_lines,
    SUM(CASE WHEN delivered_units < ordered_units THEN 1 ELSE 0 END) AS short_lines,
    SUM(ordered_units) AS units_ordered,
    SUM(LEAST(delivered_units, ordered_units)) AS units_delivered
  FROM silver.delivery_lines
  WHERE business_date = (SELECT MAX(business_date) FROM silver.delivery_lines)
  GROUP BY supplier_id
), lines AS (
  SELECT supplier_id, COUNT(*) AS lines_supplied FROM silver.products GROUP BY supplier_id
)
SELECT
  s.supplier_id,
  s.supplier_name AS supplier,
  s.category_specialism,
  s.contracted_service_level_pct,
  COALESCE(l.lines_supplied, 0) AS lines_supplied,
  COALESCE(p.delivery_lines, 0) AS delivery_lines,
  COALESCE(p.short_lines, 0) AS short_lines,
  COALESCE(p.units_ordered - p.units_delivered, 0) AS units_short,
  ROUND(100.0 * p.units_delivered / NULLIF(p.units_ordered, 0), 1) AS fill_rate_pct
FROM silver.suppliers s
LEFT JOIN perf p ON p.supplier_id = s.supplier_id
LEFT JOIN lines l ON l.supplier_id = s.supplier_id;
