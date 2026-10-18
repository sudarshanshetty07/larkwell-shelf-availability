-- Gold: distribution centres and the stores they serve.
CREATE OR REFRESH MATERIALIZED VIEW gold.dim_depot
COMMENT 'Larkwell Foods distribution centres (fictitious) and how many stores each serves.'
TBLPROPERTIES ('quality' = 'gold')
AS SELECT
  d.depot_id,
  d.depot_name AS depot,
  d.region_served AS serves,
  COUNT(s.store_id) AS stores_served
FROM silver.depots d
LEFT JOIN silver.stores s ON s.depot_id = d.depot_id
GROUP BY d.depot_id, d.depot_name, d.region_served;
