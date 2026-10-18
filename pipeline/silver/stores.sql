-- Silver: Current store master: the latest record per store.
CREATE OR REFRESH MATERIALIZED VIEW silver.stores (
  CONSTRAINT valid_store_id EXPECT (store_id RLIKE '^S[0-9]{4}$') ON VIOLATION DROP ROW,
  CONSTRAINT known_format EXPECT (store_format IN ('Superstore', 'Local', 'Travel', 'Forecourt', 'Outlet')),
  CONSTRAINT known_ownership EXPECT (ownership IN ('Owned', 'Franchise')),
  CONSTRAINT has_depot EXPECT (depot_id IS NOT NULL)
)
COMMENT 'Current store master: the latest record per store. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT store_id, store_name, division, area, store_format, ownership, depot_id, effective_date
FROM bronze.store_master
QUALIFY ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY effective_date DESC, _ingested_at DESC) = 1;
