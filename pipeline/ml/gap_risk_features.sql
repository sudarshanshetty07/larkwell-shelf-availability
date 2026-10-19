-- ML: the gap-risk model's inputs. One row per product-location per trading day.
--
-- Every value is known by the evening of the business date: that day's stock and feeds, and the six days before it.
-- The label (an unplanned gap the next morning) is not in this table. Training joins it on from the next day's row,
-- and scoring uses today's rows, so the model is trained and scored on exactly the same definitions.
--
-- Signals use the same rules as the root-cause cascade in gold: a short delivery, an order still blocked or cancelled,
-- phantom stock found by a count, waste, and an allocation cut by a market shortage.
CREATE OR REFRESH MATERIALIZED VIEW ml.gap_risk_features (
  business_date DATE COMMENT 'Trading day the features describe; all of it is known by that evening',
  store_id STRING COMMENT 'Store identifier',
  upc STRING COMMENT '13-digit barcode of the line',
  supplier_id STRING COMMENT 'Supplier identifier',
  depot_id STRING COMMENT 'Depot serving the store',
  active BOOLEAN COMMENT 'False if the line is being exited from the range: its gaps are planned, so it is never scored',
  is_gap INT COMMENT '1 if the shelf is empty this morning',
  is_low INT COMMENT '1 if the shelf is below its presentation minimum but not empty',
  on_hand INT COMMENT 'Units on the shelf at the morning snapshot',
  presentation_min INT COMMENT 'Fewest units the shelf should show',
  shelf_capacity INT COMMENT 'Most units the shelf holds',
  forecast INT COMMENT 'Forecast units for the day',
  sales INT COMMENT 'Units sold on the day',
  days_of_cover DOUBLE COMMENT 'Stock on hand divided by forecast demand',
  fill_ratio DOUBLE COMMENT 'Stock on hand divided by shelf capacity',
  sold_over_forecast INT COMMENT 'Units sold minus forecast (negative when selling below forecast)',
  short_units INT COMMENT 'Units short on today''s deliveries',
  open_blocks INT COMMENT 'Orders still blocked or cancelled today',
  phantom_units INT COMMENT 'Units of phantom stock found by today''s stock counts',
  waste_units INT COMMENT 'Units written off as waste today',
  shortage_units INT COMMENT 'Units cut from today''s allocation by a market shortage',
  gap_days_7d INT COMMENT 'Days the shelf was empty in the last 7, including today',
  exception_days_7d INT COMMENT 'Days the shelf was empty or low in the last 7, including today',
  short_days_7d INT COMMENT 'Days with a short delivery in the last 7, including today',
  block_days_7d INT COMMENT 'Days with an order blocked in the last 7, including today',
  gap_yesterday INT COMMENT '1 if the shelf was empty yesterday',
  store_gap_rate_today DOUBLE COMMENT 'Share of the store''s ranged lines empty today',
  store_gap_rate_7d DOUBLE COMMENT 'Share of the store''s ranged lines empty, over the last 7 days',
  line_gap_rate_today DOUBLE COMMENT 'Share of stores where this line is empty today',
  line_gap_rate_7d DOUBLE COMMENT 'Share of stores where this line was empty, over the last 7 days',
  line_shortage_rate_today DOUBLE COMMENT 'Share of stores whose allocation of this line was cut by a market shortage today',
  supplier_short_rate_today DOUBLE COMMENT 'Share of the supplier''s delivery lines that arrived short today',
  supplier_short_rate_3d DOUBLE COMMENT 'The same, averaged over the last 3 days',
  depot_block_rate_today DOUBLE COMMENT 'Share of the depot''s store-lines with an order blocked today',
  depot_block_rate_3d DOUBLE COMMENT 'The same, averaged over the last 3 days',
  depot_short_rate_today DOUBLE COMMENT 'Share of the depot''s delivery lines that arrived short today',
  target_dow INT COMMENT 'Day of the week being predicted (tomorrow): 0 Monday to 6 Sunday',
  shelf_life_days INT COMMENT 'Shelf life of the line in days',
  unit_price_gbp DOUBLE COMMENT 'Selling price of one unit (GBP)',
  on_promotion INT COMMENT '1 if the line is a promotional pack (2 for 5 pounds or a multi-buy)',
  CONSTRAINT line_is_mastered EXPECT (supplier_id IS NOT NULL AND depot_id IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT cover_is_valid EXPECT (days_of_cover >= 0 AND fill_ratio >= 0),
  CONSTRAINT rates_are_shares EXPECT (store_gap_rate_7d BETWEEN 0 AND 1 AND line_gap_rate_7d BETWEEN 0 AND 1
                                      AND supplier_short_rate_3d BETWEEN 0 AND 1 AND depot_block_rate_3d BETWEEN 0 AND 1)
)
COMMENT 'Larkwell Foods (fictitious) gap-risk features: one row per product-location per trading day, worked out from that day''s stock and feeds and the six days before. Inputs to the gap-risk model; the label is never stored here. Synthetic data.'
CLUSTER BY (business_date, store_id)
TBLPROPERTIES ('quality' = 'gold')
AS WITH stock AS (
  SELECT
    business_date, store_id, upc,
    range_status = 'ACTIVE' AS active,
    CASE WHEN on_hand_units = 0 AND range_status = 'ACTIVE' THEN 1 ELSE 0 END AS gap,
    CASE WHEN on_hand_units > 0 AND on_hand_units < presentation_min_units THEN 1 ELSE 0 END AS low,
    CASE WHEN on_hand_units < presentation_min_units AND range_status = 'ACTIVE' THEN 1 ELSE 0 END AS exception,
    on_hand_units, presentation_min_units, shelf_capacity_units, forecast_units, sales_units
  FROM silver.store_stock_history
), signal_rows AS (
  SELECT business_date, store_id, upc, ordered_units - delivered_units AS short, 0 AS block, 0 AS phantom, 0 AS wasted, 0 AS cut
  FROM silver.delivery_lines WHERE delivered_units < ordered_units
  UNION ALL
  SELECT business_date, store_id, upc, 0, 1, 0, 0, 0 FROM silver.order_status WHERE latest_status IN ('BLOCKED', 'CANCELLED')
  UNION ALL
  SELECT business_date, store_id, upc, 0, 0, -adjustment_units, 0, 0
  FROM silver.stock_counts WHERE adjustment_reason = 'STOCK_COUNT' AND adjustment_units < 0
  UNION ALL
  SELECT business_date, store_id, upc, 0, 0, 0, waste_units, 0 FROM silver.waste_events
  UNION ALL
  SELECT business_date, store_id, upc, 0, 0, 0, 0, requested_units - allocated_units
  FROM silver.allocations WHERE allocation_reason = 'MARKET_SHORTAGE' AND allocated_units < requested_units
), signals AS (
  SELECT business_date, store_id, upc, SUM(short) AS short_units, SUM(block) AS open_blocks,
         SUM(phantom) AS phantom_units, SUM(wasted) AS waste_units, SUM(cut) AS shortage_units
  FROM signal_rows GROUP BY business_date, store_id, upc
), cell AS (
  SELECT
    s.*, st.depot_id, pr.supplier_id, pr.shelf_life_days, pr.unit_price_gbp,
    CASE WHEN pr.product RLIKE '2 for £5|Multi-Buy' THEN 1 ELSE 0 END AS on_promotion,
    CAST(COALESCE(g.short_units, 0) AS INT) AS short_units,
    CAST(COALESCE(g.open_blocks, 0) AS INT) AS open_blocks,
    CAST(COALESCE(g.phantom_units, 0) AS INT) AS phantom_units,
    CAST(COALESCE(g.waste_units, 0) AS INT) AS waste_units,
    CAST(COALESCE(g.shortage_units, 0) AS INT) AS shortage_units
  FROM stock s
  LEFT JOIN signals g ON g.business_date = s.business_date AND g.store_id = s.store_id AND g.upc = s.upc
  LEFT JOIN gold.dim_store st ON st.store_id = s.store_id
  LEFT JOIN gold.dim_product pr ON pr.upc = s.upc
), cell_history AS (
  SELECT
    *,
    SUM(gap) OVER w7 AS gap_days_7d,
    SUM(exception) OVER w7 AS exception_days_7d,
    SUM(CASE WHEN short_units > 0 THEN 1 ELSE 0 END) OVER w7 AS short_days_7d,
    SUM(CASE WHEN open_blocks > 0 THEN 1 ELSE 0 END) OVER w7 AS block_days_7d,
    COALESCE(LAG(gap) OVER (PARTITION BY store_id, upc ORDER BY business_date), 0) AS gap_yesterday
  FROM cell
  WINDOW w7 AS (PARTITION BY store_id, upc ORDER BY business_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
), store_day AS (                       -- context rates come from stock and signals, not the joined rows, so each is cheap
  SELECT business_date, store_id, SUM(gap) AS gaps, SUM(CASE WHEN active THEN 1 ELSE 0 END) AS ranged
  FROM stock GROUP BY business_date, store_id
), store_rates AS (
  SELECT business_date, store_id, gaps / ranged AS store_gap_rate_today,
         SUM(gaps) OVER w / SUM(ranged) OVER w AS store_gap_rate_7d
  FROM store_day WINDOW w AS (PARTITION BY store_id ORDER BY business_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
), line_day AS (
  SELECT business_date, upc, SUM(gap) AS gaps, SUM(CASE WHEN active THEN 1 ELSE 0 END) AS ranged, COUNT(*) AS stores
  FROM stock GROUP BY business_date, upc
), line_cuts AS (
  SELECT business_date, upc, COUNT(*) AS cut_stores FROM signals WHERE shortage_units > 0 GROUP BY business_date, upc
), line_rates AS (
  SELECT l.business_date, l.upc, l.gaps / GREATEST(l.ranged, 1) AS line_gap_rate_today,
         COALESCE(x.cut_stores, 0) / l.stores AS line_shortage_rate_today,
         SUM(l.gaps) OVER w / GREATEST(SUM(l.ranged) OVER w, 1) AS line_gap_rate_7d
  FROM line_day l LEFT JOIN line_cuts x ON x.business_date = l.business_date AND x.upc = l.upc
  WINDOW w AS (PARTITION BY l.upc ORDER BY l.business_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
), supplier_rates AS (
  SELECT business_date, supplier_id, short_rate AS supplier_short_rate_today,
         AVG(short_rate) OVER (PARTITION BY supplier_id ORDER BY business_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS supplier_short_rate_3d
  FROM (SELECT business_date, supplier_id, CAST(AVG(CASE WHEN delivered_units < ordered_units THEN 1 ELSE 0 END) AS DOUBLE) AS short_rate
        FROM silver.delivery_lines GROUP BY business_date, supplier_id)
), depot_cells AS (
  SELECT depot_id, COUNT(*) * (SELECT COUNT(*) FROM gold.dim_product) AS cells FROM gold.dim_store GROUP BY depot_id
), depot_blocks AS (
  SELECT g.business_date, st.depot_id, COUNT(*) AS blocked_cells
  FROM signals g JOIN gold.dim_store st ON st.store_id = g.store_id
  WHERE g.open_blocks > 0 GROUP BY g.business_date, st.depot_id
), depot_shorts AS (
  SELECT business_date, depot_id, CAST(AVG(CASE WHEN delivered_units < ordered_units THEN 1 ELSE 0 END) AS DOUBLE) AS short_rate
  FROM silver.delivery_lines GROUP BY business_date, depot_id
), depot_rates AS (
  SELECT d.business_date, dc.depot_id, COALESCE(b.blocked_cells, 0) / dc.cells AS depot_block_rate_today,
         AVG(COALESCE(b.blocked_cells, 0) / dc.cells) OVER (PARTITION BY dc.depot_id ORDER BY d.business_date
                                                              ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS depot_block_rate_3d,
         COALESCE(x.short_rate, 0) AS depot_short_rate_today
  FROM (SELECT DISTINCT business_date FROM store_day) d
  CROSS JOIN depot_cells dc
  LEFT JOIN depot_blocks b ON b.business_date = d.business_date AND b.depot_id = dc.depot_id
  LEFT JOIN depot_shorts x ON x.business_date = d.business_date AND x.depot_id = dc.depot_id
)
SELECT
  c.business_date, c.store_id, c.upc, c.supplier_id, c.depot_id, c.active,
  c.gap AS is_gap, c.low AS is_low,
  c.on_hand_units AS on_hand, c.presentation_min_units AS presentation_min, c.shelf_capacity_units AS shelf_capacity,
  c.forecast_units AS forecast, c.sales_units AS sales,
  c.on_hand_units / c.forecast_units AS days_of_cover,
  c.on_hand_units / GREATEST(c.shelf_capacity_units, 1) AS fill_ratio,
  c.sales_units - c.forecast_units AS sold_over_forecast,
  c.short_units, c.open_blocks, c.phantom_units, c.waste_units, c.shortage_units,
  CAST(c.gap_days_7d AS INT) AS gap_days_7d, CAST(c.exception_days_7d AS INT) AS exception_days_7d,
  CAST(c.short_days_7d AS INT) AS short_days_7d, CAST(c.block_days_7d AS INT) AS block_days_7d,
  CAST(c.gap_yesterday AS INT) AS gap_yesterday,
  s.store_gap_rate_today, s.store_gap_rate_7d,
  l.line_gap_rate_today, l.line_gap_rate_7d, l.line_shortage_rate_today,
  COALESCE(p.supplier_short_rate_today, 0) AS supplier_short_rate_today,
  COALESCE(p.supplier_short_rate_3d, 0) AS supplier_short_rate_3d,
  d.depot_block_rate_today, d.depot_block_rate_3d, d.depot_short_rate_today,
  CAST((weekday(c.business_date) + 1) % 7 AS INT) AS target_dow,
  CAST(c.shelf_life_days AS INT) AS shelf_life_days, c.unit_price_gbp, c.on_promotion
FROM cell_history c
JOIN store_rates s ON s.business_date = c.business_date AND s.store_id = c.store_id
JOIN line_rates l ON l.business_date = c.business_date AND l.upc = c.upc
LEFT JOIN supplier_rates p ON p.business_date = c.business_date AND p.supplier_id = c.supplier_id
JOIN depot_rates d ON d.business_date = c.business_date AND d.depot_id = c.depot_id;
