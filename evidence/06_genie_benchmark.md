# Genie agent: benchmark evaluation

_Generated 2026-10-19 08:08 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

Genie space over the metric view, the gold table, supplier performance and the actions and scans views. It has 9 example SQLs, a text instruction set, and 12 benchmark questions with canonical SQL. Built by `genie/build_space.py`.

## Benchmark runs (Genie's built-in evaluation)

| run | questions | correct | status |
|---|---|---|---|
| first run | 12 | 11 | DONE |
| after the 'single total' instruction | 12 | 11 | DONE |
| after rewording the depot example | 12 | 12 | DONE |

The two misses were fixed by general instructions, not by copying benchmark answers in. Run 1: a 'how many' question returned a split instead of one total. Run 2: an example used the same wording as a benchmark question but returned a ranked list.

## Final run, question by question

| question | assessment | Genie's SQL |
|---|---|---|
| How many actionable gaps are there in Bakery? | GOOD | SELECT MEASURE(actionable_gaps) AS actionable_gaps FROM larkwell_osa.gold.mv_availability WHERE category = 'Bakery' GROUP BY ALL |
| How many gaps and lows are there in the South division? | GOOD | SELECT MEASURE(gaps) AS gaps, MEASURE(lows) AS lows FROM larkwell_osa.gold.mv_availability WHERE division = 'South' GROUP BY ALL |
| How many gaps and lows had more than one kind of evidence? | GOOD | SELECT COUNT(*) AS exceptions_with_multiple_evidence FROM larkwell_osa.gold.product_location_status WHERE issue IN ('GAP', 'LOW') AND evidence_found LIKE '%,%' |
| How many space lows are there in each category? | GOOD | SELECT category, COUNT(*) AS space_lows FROM larkwell_osa.gold.product_location_status WHERE issue = 'LOW' AND low_issue = 'SPACE_LOW' AND category IS NOT NULL GROUP BY category ORDER BY space_lows DESC, category ASC |
| What is the estimated sales at risk from supplier shorts? | GOOD | SELECT MEASURE(sales_at_risk_gbp) AS sales_at_risk_gbp FROM larkwell_osa.gold.mv_availability WHERE root_cause = 'SUPPLIER_SHORT' GROUP BY ALL |
| What is the gap rate by store format? | GOOD | SELECT store_format, MEASURE(gap_rate_pct) AS gap_rate_pct, MEASURE(gaps) AS gaps FROM larkwell_osa.gold.mv_availability WHERE store_format IS NOT NULL GROUP BY ALL ORDER BY gap_rate_pct DESC |
| What is the overall on-shelf availability? | GOOD | SELECT MEASURE(availability_pct) AS availability_pct FROM larkwell_osa.gold.mv_availability GROUP BY ALL |
| What is the root-cause mix at Covent Garden? | GOOD | SELECT consensus_reason AS root_cause, COUNT(*) AS exceptions, try_divide(100.0 * COUNT(*),SUM(COUNT(*)) OVER ()) AS share_pct FROM larkwell_osa.gold.product_location_status WHERE store = 'Covent Garden' AND issue IS NOT NULL AND issue <> 'NO_ISSUE' AND consen |
| What share of gaps and lows have a confirmed root cause? | GOOD | SELECT MEASURE(attributed_pct) AS attributed_pct FROM larkwell_osa.gold.mv_availability GROUP BY ALL |
| Which 5 suppliers have the lowest fill rate? | GOOD | WITH ranked_suppliers AS ( SELECT supplier, category_specialism, fill_rate_pct, contracted_service_level_pct, units_short, RANK() OVER (ORDER BY fill_rate_pct ASC) AS rank FROM larkwell_osa.gold.dim_supplier WHERE fill_rate_pct IS NOT NULL AND supplier IS NOT  |
| Which 5 suppliers have the most supplier shorts? | GOOD | SELECT supplier, COUNT(*) AS supplier_shorts FROM larkwell_osa.gold.product_location_status WHERE consensus_reason = 'SUPPLIER_SHORT' AND supplier IS NOT NULL GROUP BY supplier ORDER BY supplier_shorts DESC, supplier ASC LIMIT 5 |
| Which depot has the most order or delivery blocks? | GOOD | WITH depot_blocks AS ( SELECT depot, COUNT(*) AS delivery_blocks, RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk FROM larkwell_osa.gold.product_location_status WHERE consensus_reason = 'ORDER_DELIVERY_BLOCK' AND depot IS NOT NULL GROUP BY depot ) SELECT depot, de |
