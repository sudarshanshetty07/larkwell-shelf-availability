-- Gold: product_location_status. One row per product-location (store x line) for the business day.
--
-- Shelf status comes from the store stock extract:
--   GAP       nothing on the shelf (on hand = 0)
--   LOW       below the presentation minimum; SPACE_LOW if the shelf can't hold a day's forecast demand, else SALES_LOW
--   NO_ISSUE  everything else
--
-- Root cause for every GAP or LOW comes from the raw signals, checked in this order (first match wins):
--   1 KNOWN_GAP             the line is being exited from the store's range (a planned, accepted gap)
--   2 SCARCITY              a market-wide shortage cut the store's allocation
--   3 SUPPLIER_SHORT        a delivery arrived short
--   4 ORDER_DELIVERY_BLOCK  an order is still blocked, or was cancelled
--   5 STOCKFILE_ADJUSTMENT  a stock count found phantom stock, so the system believed there was stock and didn't reorder
--   6 WASTE                 stock was written off as waste
--   7 UNDER_FORECAST        the line sold more than its forecast
--   8 INVESTIGATE           no evidence found, so a person needs to look
-- Upstream causes come first because they explain why stock never arrived; store causes and demand come after.
-- The evidence columns describe the chosen root cause. evidence_found lists every kind of evidence present.
CREATE OR REFRESH MATERIALIZED VIEW gold.product_location_status (
  store STRING COMMENT 'Store name',
  division STRING COMMENT 'Store division: North & Scotland, Central or South',
  area STRING COMMENT 'Store area within a division',
  site_trading_group STRING COMMENT 'Store format: Superstore, Local, Travel, Forecourt or Outlet',
  cluster STRING COMMENT 'Temperature cluster: Ambient, Chilled or Frozen',
  super_group STRING COMMENT 'Department, e.g. Fresh Foods, Chilled, Grocery',
  category STRING COMMENT 'Product category, e.g. Bakery, Dairy, Ready Meals',
  product_group STRING COMMENT 'Product group within a category',
  product STRING COMMENT 'Product (line) name',
  upc STRING COMMENT '13-digit barcode of the line',
  supplier STRING COMMENT 'Supplier of the line',
  depot STRING COMMENT 'Distribution centre serving the store',
  business_scope STRING COMMENT 'Owned or Franchise store',
  issue STRING COMMENT 'Shelf status: GAP (empty), LOW (below the presentation minimum) or NO_ISSUE',
  low_issue STRING COMMENT 'For LOW only: SALES_LOW (selling faster than planned) or SPACE_LOW (shelf too small for a day of demand)',
  consensus_reason STRING COMMENT 'Root cause from the rules cascade (head office view); NULL when issue = NO_ISSUE',
  consensus_reason_retail STRING COMMENT 'Root cause for store teams (retail view); NULL when issue = NO_ISSUE',
  known_gap BOOLEAN COMMENT 'True if the root cause is a deliberate, pre-agreed gap (range exit)',
  supplier_short BOOLEAN COMMENT 'True if the root cause is a short delivery',
  supplier_short_type STRING COMMENT 'For supplier shorts: DEPOT_SHORT, LOGISTICS_DELAY, PRODUCTION_ISSUE or RAW_MATERIAL_SHORTAGE',
  scarcity BOOLEAN COMMENT 'True if the root cause is a market-wide shortage',
  waste BOOLEAN COMMENT 'True if the root cause is stock lost to waste',
  under_forecast BOOLEAN COMMENT 'True if the root cause is demand above forecast',
  order_delivery_block BOOLEAN COMMENT 'True if the root cause is a blocked or cancelled order',
  upstream_issue BOOLEAN COMMENT 'True if the cause is above the store: supplier short, scarcity or an order/delivery block',
  elimination BOOLEAN COMMENT 'Reserved: line deletion flag (always false in this build)',
  msc_decrease BOOLEAN COMMENT 'Reserved: planned allocation cut flag (always false in this build)',
  supplier_short_qty DOUBLE COMMENT 'Units short against the order (when the root cause is SUPPLIER_SHORT)',
  scarcity_qty DOUBLE COMMENT 'Units cut from the allocation by the market shortage (when the root cause is SCARCITY)',
  waste_qty DOUBLE COMMENT 'Units written off as waste (when the root cause is WASTE)',
  under_forecast_qty DOUBLE COMMENT 'Units sold above forecast (when the root cause is UNDER_FORECAST)',
  under_space_qty DOUBLE COMMENT 'Units of daily demand above shelf capacity (for SPACE_LOW)',
  stockfile_adjustment_qty DOUBLE COMMENT 'Units of phantom stock found by the count (when the root cause is STOCKFILE_ADJUSTMENT)',
  business_date DATE COMMENT 'Trading day the snapshot describes',
  store_id STRING COMMENT 'Store identifier',
  supplier_id STRING COMMENT 'Supplier identifier',
  depot_id STRING COMMENT 'Depot identifier',
  on_hand_units INT COMMENT 'Units on the shelf at the morning snapshot',
  presentation_min_units INT COMMENT 'Fewest units the shelf should show',
  shelf_capacity_units INT COMMENT 'Most units the shelf holds',
  forecast_units INT COMMENT 'Forecast units for the day',
  sales_units INT COMMENT 'Units sold on the trading day',
  days_of_cover DOUBLE COMMENT 'Days of forecast demand the stock on hand covers',
  unit_price_gbp DOUBLE COMMENT 'Selling price of one unit (GBP)',
  est_sales_at_risk_gbp DOUBLE COMMENT 'Estimate: forecast demand not covered by stock on hand, valued at selling price (GAP and LOW only)',
  evidence_found STRING COMMENT 'Every kind of evidence present for this product-location, comma-separated, in cascade order',
  CONSTRAINT exception_has_root_cause EXPECT (issue = 'NO_ISSUE' OR consensus_reason IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT healthy_shelf_has_no_root_cause EXPECT (issue <> 'NO_ISSUE' OR consensus_reason IS NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT product_location_is_mastered EXPECT (store IS NOT NULL AND product IS NOT NULL) ON VIOLATION FAIL UPDATE
)
COMMENT 'Larkwell Foods (fictitious) on-shelf availability: shelf status and root cause for every product-location, worked out from the raw store, delivery, order, stock-count, waste and allocation feeds. One row per store x line for the business day. Synthetic data.'
CLUSTER BY (store, upc)
TBLPROPERTIES ('quality' = 'gold')
AS WITH snapshot AS (
  -- The latest business day in the stock extract. Every signal below is read for that day only.
  SELECT MAX(business_date) AS business_date FROM silver.store_stock
), stock AS (
  SELECT
    business_date, store_id, upc, range_status, on_hand_units, presentation_min_units, shelf_capacity_units,
    forecast_units, sales_units,
    CASE
      WHEN on_hand_units = 0 THEN 'GAP'
      WHEN on_hand_units < presentation_min_units THEN 'LOW'
      ELSE 'NO_ISSUE'
    END AS issue
  FROM silver.store_stock
  WHERE business_date = (SELECT business_date FROM snapshot)
), shortage AS (
  SELECT store_id, upc, SUM(requested_units - allocated_units) AS shortage_units
  FROM silver.allocations
  WHERE business_date = (SELECT business_date FROM snapshot)
    AND allocation_reason = 'MARKET_SHORTAGE' AND allocated_units < requested_units
  GROUP BY store_id, upc
), shorts AS (
  SELECT
    store_id, upc,
    SUM(ordered_units - delivered_units) AS short_units,
    MAX_BY(short_reason, ordered_units - delivered_units) AS short_reason
  FROM silver.delivery_lines
  WHERE business_date = (SELECT business_date FROM snapshot) AND delivered_units < ordered_units
  GROUP BY store_id, upc
), blocks AS (
  SELECT store_id, upc, COUNT(*) AS open_blocks
  FROM silver.order_status
  WHERE business_date = (SELECT business_date FROM snapshot) AND latest_status IN ('BLOCKED', 'CANCELLED')
  GROUP BY store_id, upc
), phantom AS (
  SELECT store_id, upc, -SUM(adjustment_units) AS phantom_units
  FROM silver.stock_counts
  WHERE business_date = (SELECT business_date FROM snapshot)
    AND adjustment_reason = 'STOCK_COUNT' AND adjustment_units < 0
  GROUP BY store_id, upc
), wasted AS (
  SELECT store_id, upc, SUM(waste_units) AS waste_units
  FROM silver.waste_events
  WHERE business_date = (SELECT business_date FROM snapshot)
  GROUP BY store_id, upc
), evidence AS (
  SELECT
    s.*,
    s.range_status = 'EXITING' AS range_exit,
    COALESCE(sh.shortage_units, 0) AS shortage_units,
    COALESCE(ss.short_units, 0) AS short_units,
    ss.short_reason,
    COALESCE(b.open_blocks, 0) AS open_blocks,
    COALESCE(p.phantom_units, 0) AS phantom_units,
    COALESCE(w.waste_units, 0) AS waste_units,
    GREATEST(s.sales_units - s.forecast_units, 0) AS demand_above_forecast
  FROM stock s
  LEFT JOIN shortage sh ON sh.store_id = s.store_id AND sh.upc = s.upc
  LEFT JOIN shorts ss ON ss.store_id = s.store_id AND ss.upc = s.upc
  LEFT JOIN blocks b ON b.store_id = s.store_id AND b.upc = s.upc
  LEFT JOIN phantom p ON p.store_id = s.store_id AND p.upc = s.upc
  LEFT JOIN wasted w ON w.store_id = s.store_id AND w.upc = s.upc
), classified AS (
  SELECT
    *,
    CASE WHEN issue = 'LOW' THEN
      CASE WHEN shelf_capacity_units < forecast_units THEN 'SPACE_LOW' ELSE 'SALES_LOW' END
    END AS low_issue,
    CASE
      WHEN issue = 'NO_ISSUE' THEN NULL
      WHEN range_exit THEN 'KNOWN_GAP'
      WHEN shortage_units > 0 THEN 'SCARCITY'
      WHEN short_units > 0 THEN 'SUPPLIER_SHORT'
      WHEN open_blocks > 0 THEN 'ORDER_DELIVERY_BLOCK'
      WHEN phantom_units > 0 THEN 'STOCKFILE_ADJUSTMENT'
      WHEN waste_units > 0 THEN 'WASTE'
      WHEN demand_above_forecast > 0 THEN 'UNDER_FORECAST'
      ELSE 'INVESTIGATE'
    END AS consensus_reason,
    concat_ws(',',
      CASE WHEN range_exit THEN 'KNOWN_GAP' END,
      CASE WHEN shortage_units > 0 THEN 'SCARCITY' END,
      CASE WHEN short_units > 0 THEN 'SUPPLIER_SHORT' END,
      CASE WHEN open_blocks > 0 THEN 'ORDER_DELIVERY_BLOCK' END,
      CASE WHEN phantom_units > 0 THEN 'STOCKFILE_ADJUSTMENT' END,
      CASE WHEN waste_units > 0 THEN 'WASTE' END,
      CASE WHEN demand_above_forecast > 0 THEN 'UNDER_FORECAST' END
    ) AS evidence_found
  FROM evidence
)
SELECT
  st.store,
  st.division,
  st.area,
  st.site_trading_group,
  pr.cluster,
  pr.super_group,
  pr.category,
  pr.product_group,
  pr.product,
  c.upc,
  pr.supplier,
  st.depot,
  st.business_scope,
  c.issue,
  c.low_issue,
  c.consensus_reason,
  c.consensus_reason AS consensus_reason_retail,
  COALESCE(c.consensus_reason = 'KNOWN_GAP', false) AS known_gap,
  COALESCE(c.consensus_reason = 'SUPPLIER_SHORT', false) AS supplier_short,
  CASE WHEN c.consensus_reason = 'SUPPLIER_SHORT' THEN COALESCE(c.short_reason, '') ELSE '' END AS supplier_short_type,
  COALESCE(c.consensus_reason = 'SCARCITY', false) AS scarcity,
  COALESCE(c.consensus_reason = 'WASTE', false) AS waste,
  COALESCE(c.consensus_reason = 'UNDER_FORECAST', false) AS under_forecast,
  COALESCE(c.consensus_reason = 'ORDER_DELIVERY_BLOCK', false) AS order_delivery_block,
  COALESCE(c.consensus_reason IN ('SUPPLIER_SHORT', 'SCARCITY', 'ORDER_DELIVERY_BLOCK'), false) AS upstream_issue,
  false AS elimination,
  false AS msc_decrease,
  CAST(CASE WHEN c.consensus_reason = 'SUPPLIER_SHORT' THEN c.short_units ELSE 0 END AS DOUBLE) AS supplier_short_qty,
  CAST(CASE WHEN c.consensus_reason = 'SCARCITY' THEN c.shortage_units ELSE 0 END AS DOUBLE) AS scarcity_qty,
  CAST(CASE WHEN c.consensus_reason = 'WASTE' THEN c.waste_units ELSE 0 END AS DOUBLE) AS waste_qty,
  CAST(CASE WHEN c.consensus_reason = 'UNDER_FORECAST' THEN c.demand_above_forecast ELSE 0 END AS DOUBLE) AS under_forecast_qty,
  CAST(CASE WHEN c.low_issue = 'SPACE_LOW' THEN c.forecast_units - c.shelf_capacity_units ELSE 0 END AS DOUBLE) AS under_space_qty,
  CAST(CASE WHEN c.consensus_reason = 'STOCKFILE_ADJUSTMENT' THEN c.phantom_units ELSE 0 END AS DOUBLE) AS stockfile_adjustment_qty,
  c.business_date,
  c.store_id,
  pr.supplier_id,
  st.depot_id,
  c.on_hand_units,
  c.presentation_min_units,
  c.shelf_capacity_units,
  c.forecast_units,
  c.sales_units,
  CAST(ROUND(c.on_hand_units / c.forecast_units, 1) AS DOUBLE) AS days_of_cover,
  pr.unit_price_gbp,
  CAST(CASE WHEN c.issue <> 'NO_ISSUE'
    THEN ROUND(GREATEST(c.forecast_units - c.on_hand_units, 0) * pr.unit_price_gbp, 2) ELSE 0 END AS DOUBLE) AS est_sales_at_risk_gbp,
  c.evidence_found
FROM classified c
LEFT JOIN gold.dim_store st ON st.store_id = c.store_id
LEFT JOIN gold.dim_product pr ON pr.upc = c.upc;
