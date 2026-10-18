-- Gold: stores with their serving depot.
CREATE OR REFRESH MATERIALIZED VIEW gold.dim_store (
  CONSTRAINT store_has_depot EXPECT (depot IS NOT NULL) ON VIOLATION FAIL UPDATE
)
COMMENT 'Larkwell Foods stores (fictitious): division > area > format (site_trading_group) > store, with ownership and the depot that serves each store.'
TBLPROPERTIES ('quality' = 'gold')
AS SELECT
  s.store_id,
  s.store_name AS store,
  s.division,
  s.area,
  s.store_format AS site_trading_group,
  s.ownership AS business_scope,
  s.depot_id,
  d.depot_name AS depot
FROM silver.stores s
LEFT JOIN silver.depots d ON d.depot_id = s.depot_id;
