-- Silver: Current distribution centre master.
CREATE OR REFRESH MATERIALIZED VIEW silver.depots (
  CONSTRAINT valid_depot_id EXPECT (depot_id RLIKE '^D[0-9]{2}$') ON VIOLATION DROP ROW
)
COMMENT 'Current distribution centre master. Synthetic data: Larkwell Foods is fictitious.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT depot_id, depot_name, region_served, effective_date
FROM bronze.depot_master
QUALIFY ROW_NUMBER() OVER (PARTITION BY depot_id ORDER BY effective_date DESC, _ingested_at DESC) = 1;
