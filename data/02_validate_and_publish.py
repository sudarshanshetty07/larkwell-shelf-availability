# Databricks notebook source
# MAGIC %md
# MAGIC # 2 · Check the day's data and publish the results
# MAGIC
# MAGIC Runs after the Lakeflow pipeline and the Lakebase sync. It checks every stage of the journey:
# MAGIC
# MAGIC | Stage | Check |
# MAGIC |---|---|
# MAGIC | Raw | Files and rows landed, from the source systems' manifest |
# MAGIC | Bronze | Every feed ingested row for row against the manifest |
# MAGIC | Silver | Exactly the malformed rows dropped and the re-sent duplicates removed |
# MAGIC | Gold | Headline counts, the reason mix, and a row-by-row match against the answer key; hard constraints held |
# MAGIC | Governance | The metric view's gap rate agrees with the table |
# MAGIC | Lakebase | The synced copy matches gold |
# MAGIC | ML | The gap-risk features cover every product-location and agree with gold |
# MAGIC
# MAGIC Every result is written to `ops.pipeline_checks`, which the app's Data Journey tab reads.
# MAGIC The run fails if any check fails.

# COMMAND ----------

dbutils.widgets.text("catalog", "larkwell_osa")
dbutils.widgets.text("business_date", "2026-10-17")
dbutils.widgets.text("pipeline_id", "")
dbutils.widgets.text("lakebase_catalog", "larkwell_osa_pg")
CATALOG = dbutils.widgets.get("catalog")
BUSINESS_DATE = dbutils.widgets.get("business_date")
PIPELINE_ID = dbutils.widgets.get("pipeline_id")
LB_CATALOG = dbutils.widgets.get("lakebase_catalog")

import datetime
import json
import uuid

RUN_ID = str(uuid.uuid4())
RUN_AT = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
# A job repair doesn't carry run-time parameters over, so a repaired task can be handed the default date. One was: it
# checked 2026-10-17 while gold held 2026-10-18, and passed only because the synthetic days share a seed. Refuse instead.
GOLD_DATE = str(spark.sql(f"SELECT MAX(business_date) AS d FROM {CATALOG}.gold.product_location_status").first().d)
assert GOLD_DATE == BUSINESS_DATE, f"Gold holds {GOLD_DATE}, but this run was asked to check {BUSINESS_DATE}: pass business_date"
manifest = json.load(open(f"/Volumes/{CATALOG}/raw/landing/_manifests/{BUSINESS_DATE}.json"))
expected = json.load(open(f"/Volumes/{CATALOG}/raw/answer_key/{BUSINESS_DATE}/expected_counts.json"))
checks = []


def check(order, stage, metric, value, expect=None, passed=None, note=""):
    value = float(value) if value is not None else None
    expect = float(expect) if expect is not None else None
    if passed is None:
        passed = expect is None or value == expect
    checks.append({"run_id": RUN_ID, "run_at": RUN_AT, "business_date": datetime.date.fromisoformat(BUSINESS_DATE),
                   "stage_order": order, "stage": stage, "metric": metric, "value": value, "expected": expect,
                   "passed": bool(passed), "note": note})


def one(sql):
    return spark.sql(sql).first()

# COMMAND ----------

# MAGIC %md ## Raw and bronze: everything that landed was ingested

# COMMAND ----------

feeds = manifest["feeds"]
check(1, "raw", "files_landed", sum(len(f["files"]) for f in feeds.values()), passed=True)
rows_landed = sum(f["rows"] for f in feeds.values())
check(1, "raw", "rows_landed", rows_landed, passed=rows_landed > 0)

bronze_total = 0
for feed, info in feeds.items():
    n = one(f"SELECT COUNT(*) AS n FROM {CATALOG}.bronze.{feed} WHERE _source_file LIKE '%/{BUSINESS_DATE}/%'").n
    bronze_total += n
    check(2, "bronze", f"rows_{feed}", n, info["rows"], note="matches the source manifest")
check(2, "bronze", "rows_ingested", bronze_total, rows_landed, note="matches the source manifest")

# COMMAND ----------

# MAGIC %md ## Silver: exactly the bad rows dropped, exactly the duplicates removed

# COMMAND ----------

d = one(f"""SELECT COUNT(*) AS bronze_rows, COUNT(DISTINCT delivery_line_id) AS distinct_ids,
                  (SELECT COUNT(*) FROM {CATALOG}.silver.delivery_lines WHERE business_date = '{BUSINESS_DATE}') AS silver_rows
           FROM {CATALOG}.bronze.deliveries WHERE _source_file LIKE '%/{BUSINESS_DATE}/%'""")
check(3, "silver", "duplicates_removed", d.bronze_rows - d.distinct_ids, expected["duplicate_delivery_lines"],
      note="re-sent delivery lines")
check(3, "silver", "rows_dropped", d.distinct_ids - d.silver_rows, expected["malformed_delivery_lines"],
      note="malformed delivery lines: no store, bad barcode or negative units")

latest_update = one(f"""SELECT origin.update_id AS u FROM event_log('{PIPELINE_ID}')
    WHERE event_type = 'update_progress' AND details:update_progress.state = 'COMPLETED'
    ORDER BY timestamp DESC LIMIT 1""").u
dq = spark.sql(f"""SELECT origin.flow_name AS dataset, e.name AS expectation,
        SUM(e.passed_records) AS passed, SUM(e.failed_records) AS failed
    FROM event_log('{PIPELINE_ID}')
    LATERAL VIEW explode(from_json(details:flow_progress.data_quality.expectations,
        'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) t AS e
    WHERE event_type = 'flow_progress' AND origin.update_id = '{latest_update}'
    GROUP BY 1, 2""").collect()
check(3, "silver", "expectations_evaluated", len(dq), passed=len(dq) > 0, note=f"pipeline update {latest_update}")
check(3, "silver", "expectation_violations", sum(r.failed for r in dq), passed=True,
      note="dropped rows plus warnings (over-deliveries are kept and flagged)")
hard = [r for r in dq if r.dataset.endswith(".gold.product_location_status")]
check(4, "gold", "hard_constraint_failures", sum(r.failed for r in hard), 0,
      note="every gap or low has a root cause, healthy shelves have none, every row is mastered")

# COMMAND ----------

# MAGIC %md ## Gold: the headline numbers and a row-by-row match against the answer key

# COMMAND ----------

G = f"{CATALOG}.gold.product_location_status"
g = one(f"""SELECT COUNT(*) AS pls, SUM(CASE WHEN issue = 'GAP' THEN 1 ELSE 0 END) AS gaps,
       SUM(CASE WHEN issue = 'LOW' THEN 1 ELSE 0 END) AS lows,
       SUM(CASE WHEN low_issue = 'SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
       SUM(CASE WHEN low_issue = 'SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows,
       SUM(CASE WHEN business_scope = 'Owned' THEN 1 ELSE 0 END) AS owned,
       SUM(CASE WHEN issue <> 'NO_ISSUE' AND evidence_found LIKE '%,%' THEN 1 ELSE 0 END) AS multi_evidence
    FROM {G}""")
check(4, "gold", "product_locations", g.pls, expected["product_locations"])
check(4, "gold", "gaps", g.gaps, expected["gaps"])
check(4, "gold", "lows", g.lows, expected["lows"])
check(4, "gold", "exceptions", g.gaps + g.lows, expected["gaps"] + expected["lows"])
check(4, "gold", "sales_lows", g.sales_lows, expected["sales_lows"])
check(4, "gold", "space_lows", g.space_lows, expected["space_lows"])
check(4, "gold", "owned_product_locations", g.owned, expected["owned_product_locations"])
check(4, "gold", "multi_evidence_exceptions", g.multi_evidence, passed=True,
      note="exceptions where the cascade had to choose between several kinds of evidence")
mix = {r.consensus_reason: r.n for r in spark.sql(
    f"SELECT consensus_reason, COUNT(*) AS n FROM {G} WHERE issue <> 'NO_ISSUE' GROUP BY 1").collect()}
for reason in sorted(set(expected["reason_mix"]) | set(mix)):          # every expected cause, even if it vanished
    check(4, "gold", f"reason_{reason.lower()}", mix.get(reason, 0), expected["reason_mix"].get(reason, 0))

key = f"read_files('/Volumes/{CATALOG}/raw/answer_key/{BUSINESS_DATE}/exceptions.parquet', format => 'parquet')"
m = one(f"""SELECT COUNT(*) AS key_rows,
       SUM(CASE WHEN g.issue <=> k.issue AND g.low_issue <=> k.low_issue AND g.consensus_reason <=> k.consensus_reason
                 AND g.supplier_short_type <=> k.supplier_short_type AND g.supplier_short_qty = k.supplier_short_qty
                 AND g.scarcity_qty = k.scarcity_qty AND g.waste_qty = k.waste_qty
                 AND g.under_forecast_qty = k.under_forecast_qty AND g.under_space_qty = k.under_space_qty
                 AND g.stockfile_adjustment_qty = k.stockfile_adjustment_qty THEN 1 ELSE 0 END) AS matches
    FROM {key} k LEFT JOIN {G} g ON g.store_id = k.store_id AND g.upc = k.upc""")
check(4, "gold", "answer_key_matches", m.matches, m.key_rows,
      note="status, low type, root cause, short type and all six quantities, row by row")
attributed = one(f"""SELECT ROUND(100.0 * SUM(CASE WHEN consensus_reason <> 'INVESTIGATE' THEN 1 ELSE 0 END) / COUNT(*), 1) AS p
    FROM {G} WHERE issue <> 'NO_ISSUE'""").p
check(4, "gold", "attributed_pct", attributed, passed=True, note="share of gaps and lows with a confirmed root cause")

# COMMAND ----------

# MAGIC %md ## Governance and Lakebase

# COMMAND ----------

mv = one(f"SELECT MEASURE(availability_pct) AS osa, MEASURE(gap_rate_pct) AS gap_rate FROM {CATALOG}.gold.mv_availability")
table_gap_rate = round(100.0 * g.gaps / g.pls, 2)
check(5, "governance", "availability_pct", mv.osa, passed=True, note="from the governed metric view")
check(5, "governance", "metric_view_gap_rate_pct", mv.gap_rate, table_gap_rate, note="metric view agrees with the table")
lb = one(f"""SELECT COUNT(*) AS n, SUM(CASE WHEN issue <> 'NO_ISSUE' THEN 1 ELSE 0 END) AS exceptions
    FROM {LB_CATALOG}.serving.product_location_status""")
check(6, "lakebase", "synced_rows", lb.n, g.pls, note="Lakebase copy for Shelf Scan")
check(6, "lakebase", "synced_exceptions", lb.exceptions, g.gaps + g.lows)

# COMMAND ----------

# MAGIC %md ## The gap-risk model's inputs

# COMMAND ----------

F = f"{CATALOG}.ml.gap_risk_features"
fr = one(f"SELECT COUNT(*) AS n, SUM(is_gap) AS gaps FROM {F} WHERE business_date = '{BUSINESS_DATE}'")
unplanned = one(f"SELECT COUNT(*) AS n FROM {G} WHERE issue = 'GAP' AND consensus_reason <> 'KNOWN_GAP'").n
history = one(f"SELECT COUNT(DISTINCT business_date) AS n FROM {F} WHERE business_date <= '{BUSINESS_DATE}'").n
check(7, "ml", "feature_rows", fr.n, g.pls, note="one row of gap-risk features per product-location")
check(7, "ml", "feature_gaps_match_gold", fr.gaps, unplanned, note="unplanned gaps in the features agree with gold")
check(7, "ml", "feature_history_days", history, passed=history >= 7, note="days of features; scoring needs the last 7")

# COMMAND ----------

# MAGIC %md ## Publish and fail on any failed check

# COMMAND ----------

spark.sql(f"""CREATE TABLE IF NOT EXISTS {CATALOG}.ops.pipeline_checks (
  run_id STRING, run_at TIMESTAMP, business_date DATE, stage_order INT, stage STRING, metric STRING,
  value DOUBLE, expected DOUBLE, passed BOOLEAN, note STRING)
  COMMENT 'Results of the daily checks on every stage of the data journey; read by the app''s Data Journey tab'""")
spark.createDataFrame(checks).select("run_id", "run_at", "business_date", "stage_order", "stage", "metric", "value",
                                     "expected", "passed", "note").write.mode("append").saveAsTable(f"{CATALOG}.ops.pipeline_checks")

failed = [c for c in checks if not c["passed"]]
for c in checks:
    exp = "" if c["expected"] is None else f" (expected {c['expected']:,.0f})"
    print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['stage']:<10} {c['metric']:<32} {c['value']:>14,.2f}{exp}  {c['note']}")
summary = {"run_id": RUN_ID, "business_date": BUSINESS_DATE, "checks": len(checks), "failed": len(failed),
           "failed_checks": [f"{c['stage']}.{c['metric']}" for c in failed]}
print(json.dumps(summary))
assert not failed, f"{len(failed)} checks failed: {summary['failed_checks']}"
dbutils.notebook.exit(json.dumps(summary))
