-- Governed availability KPIs: one definition of gap rate, availability, attribution and sales at risk,
-- shared by Genie, the app and anyone querying with SQL (MEASURE(gap_rate_pct) etc.).
CREATE OR REPLACE VIEW larkwell_osa.gold.mv_availability
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: larkwell_osa.gold.product_location_status
comment: "Governed on-shelf availability KPIs for Larkwell Foods (fictitious retailer, synthetic data): gap rate, availability, actionable gaps, root-cause attribution and estimated sales at risk."
dimensions:
  - name: business_date
    expr: business_date
    comment: "Trading day of the snapshot"
  - name: division
    expr: division
    comment: "Store division: North & Scotland, Central or South"
    synonyms: ["region"]
  - name: area
    expr: area
    comment: "Store area within a division"
  - name: store
    expr: store
    synonyms: ["shop", "branch"]
  - name: store_format
    expr: site_trading_group
    comment: "Superstore, Local, Travel, Forecourt or Outlet"
    synonyms: ["format", "store type"]
  - name: ownership
    expr: business_scope
    comment: "Owned or Franchise store"
  - name: department
    expr: super_group
  - name: category
    expr: category
  - name: product_group
    expr: product_group
  - name: supplier
    expr: supplier
    synonyms: ["vendor"]
  - name: depot
    expr: depot
    synonyms: ["distribution centre", "DC"]
  - name: shelf_status
    expr: issue
    comment: "GAP (empty), LOW (below the presentation minimum) or NO_ISSUE"
  - name: low_type
    expr: low_issue
    comment: "For lows: SALES_LOW or SPACE_LOW"
  - name: root_cause
    expr: consensus_reason
    comment: "Root cause from the rules cascade; NULL for healthy shelves"
    synonyms: ["reason", "reason code", "cause"]
measures:
  - name: product_locations
    expr: COUNT(1)
    comment: "Store x line combinations in scope"
  - name: gaps
    expr: COUNT(1) FILTER (WHERE issue = 'GAP')
    comment: "Empty shelves"
    synonyms: ["empty shelves", "out of stocks"]
  - name: lows
    expr: COUNT(1) FILTER (WHERE issue = 'LOW')
    comment: "Shelves below their presentation minimum"
  - name: exceptions
    expr: COUNT(1) FILTER (WHERE issue <> 'NO_ISSUE')
    comment: "Gaps plus lows"
  - name: actionable_gaps
    expr: COUNT(1) FILTER (WHERE issue = 'GAP' AND consensus_reason <> 'KNOWN_GAP')
    comment: "Gaps excluding deliberate range exits"
  - name: attributed_exceptions
    expr: COUNT(1) FILTER (WHERE issue <> 'NO_ISSUE' AND consensus_reason <> 'INVESTIGATE')
    comment: "Gaps and lows with a confirmed root cause"
  - name: gap_rate_pct
    expr: "ROUND(100.0 * MEASURE(gaps) / MEASURE(product_locations), 2)"
    comment: "Gaps as a percentage of all product-locations in scope"
  - name: availability_pct
    expr: "ROUND(100.0 - 100.0 * MEASURE(gaps) / MEASURE(product_locations), 2)"
    comment: "On-shelf availability: the percentage of product-locations that are not empty"
    synonyms: ["on-shelf availability", "OSA"]
  - name: attributed_pct
    expr: "ROUND(100.0 * MEASURE(attributed_exceptions) / MEASURE(exceptions), 1)"
    comment: "Share of gaps and lows with a confirmed root cause"
  - name: sales_at_risk_gbp
    expr: ROUND(SUM(est_sales_at_risk_gbp), 0)
    comment: "Estimate: forecast demand not covered by stock on hand, valued at selling price"
  - name: actionable_sales_at_risk_gbp
    expr: ROUND(SUM(est_sales_at_risk_gbp) FILTER (WHERE consensus_reason <> 'KNOWN_GAP'), 0)
    comment: "Estimate of sales at risk, excluding deliberate range exits"
$$
