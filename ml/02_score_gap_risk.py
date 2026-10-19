# Databricks notebook source
# MAGIC %md
# MAGIC # ML 2 · Grade yesterday's predictions, then predict tomorrow's gaps
# MAGIC
# MAGIC Runs in the daily job after the pipeline and its checks. Two steps, in this order:
# MAGIC 1. **Grade.** Yesterday's predictions for today are compared with this morning's actual shelves: the
# MAGIC    estate's AUC, and for every store, how many lines on its watch list really were empty. Results go to
# MAGIC    `ops.gap_risk_grades`, so the model is marked every single day, not just when it's trained.
# MAGIC 2. **Predict.** The `champion` version of `ml.gap_risk` in Unity Catalog scores every ranged product-location for
# MAGIC    tomorrow morning. Each store's riskiest lines get the three strongest reasons in plain English, from the model's own
# MAGIC    per-feature contributions. Results go to `ml.gap_risk_scores`, which the app's morning briefing reads.
# MAGIC
# MAGIC The run fails if the inputs are incomplete or the predictions don't look like a probability of tomorrow's gaps.

# COMMAND ----------

# MAGIC %pip install -q "mlflow[databricks]>=3.1" "lightgbm==4.6.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "larkwell_osa")
dbutils.widgets.text("business_date", "2026-10-19")
dbutils.widgets.text("reasons_per_store", "50")
CATALOG = dbutils.widgets.get("catalog")
BUSINESS_DATE = dbutils.widgets.get("business_date")
REASONS_PER_STORE = int(dbutils.widgets.get("reasons_per_store"))
FEATURE_TABLE = f"{CATALOG}.ml.gap_risk_features"
SCORES = f"{CATALOG}.ml.gap_risk_scores"
GRADES = f"{CATALOG}.ops.gap_risk_grades"
MODEL_NAME = f"{CATALOG}.ml.gap_risk"

import datetime
import json
import os
import sys

import mlflow
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from sklearn.metrics import roc_auc_score

NOTEBOOK_DIR = os.path.dirname(dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get())
sys.path.insert(0, f"/Workspace{NOTEBOOK_DIR}")
import gap_risk as gr  # noqa: E402  ml/gap_risk.py: features, rules, metrics, reasons

mlflow.set_registry_uri("databricks-uc")
TODAY = datetime.date.fromisoformat(BUSINESS_DATE)
TOMORROW = TODAY + datetime.timedelta(days=1)
RUN_AT = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
lines = spark.sql(f"SELECT COUNT(*) AS n FROM {FEATURE_TABLE} WHERE business_date = DATE'{TODAY}'").first().n
expected = spark.sql(f"SELECT COUNT(*) AS n FROM {CATALOG}.silver.store_stock_history WHERE business_date = DATE'{TODAY}'").first().n
assert lines > 0 and lines == expected, f"Features for {TODAY} are incomplete: {lines:,} rows for {expected:,} product-locations"

# COMMAND ----------

# MAGIC %md ## 1 · Grade yesterday's predictions against this morning's shelves

# COMMAND ----------

spark.sql(f"""CREATE TABLE IF NOT EXISTS {GRADES} (
  graded_date DATE COMMENT 'Morning whose shelves were checked', predicted_on DATE COMMENT 'Evening the predictions were made',
  scope STRING COMMENT 'estate, or a store name', store_id STRING, model_version STRING,
  lines BIGINT COMMENT 'Ranged lines that were scored', empty BIGINT COMMENT 'Of those, empty this morning (unplanned)',
  auc DOUBLE COMMENT 'Estate only: how well the risk ranked empty above not-empty (0.5 is chance)',
  listed BIGINT COMMENT 'Lines on the watch lists (the top 25 per store)', listed_empty BIGINT COMMENT 'Of those, empty this morning',
  list_precision DOUBLE COMMENT 'Share of watch-list lines that were empty', list_capture DOUBLE COMMENT 'Share of empty lines that were on a watch list',
  fine_listed BIGINT COMMENT 'Lines that looked fine the day before, on the looks-fine watch lists (top 25 per store)',
  fine_listed_empty BIGINT COMMENT 'Of those, empty this morning',
  predicted_rate DOUBLE COMMENT 'Mean predicted risk', observed_rate DOUBLE COMMENT 'Share of scored lines that were empty',
  graded_at TIMESTAMP)
  COMMENT 'The gap-risk model, graded every morning: last evening''s predictions against this morning''s actual shelves'""")
predicted = spark.sql(f"SELECT COUNT(*) AS n FROM {SCORES} WHERE target_date = DATE'{TODAY}'").first().n \
    if spark.catalog.tableExists(SCORES) else 0
if predicted:
    graded = f"""
        SELECT s.store_id, s.store, s.model_version, s.risk, s.risk_rank <= {gr.LIST_SIZE} AS listed,
               COALESCE(s.fine_rank <= {gr.LIST_SIZE}, false) AS fine_listed, f.is_gap AS was_empty
        FROM {SCORES} s JOIN {FEATURE_TABLE} f
          ON f.store_id = s.store_id AND f.upc = s.upc AND f.business_date = s.target_date
        WHERE s.target_date = DATE'{TODAY}'"""
    by_store = spark.sql(f"""
        SELECT store_id, store AS scope, MAX(model_version) AS model_version, COUNT(*) AS lines, SUM(was_empty) AS empty,
               SUM(CAST(listed AS INT)) AS listed, SUM(CASE WHEN listed THEN was_empty ELSE 0 END) AS listed_empty,
               SUM(CAST(fine_listed AS INT)) AS fine_listed, SUM(CASE WHEN fine_listed THEN was_empty ELSE 0 END) AS fine_listed_empty,
               AVG(risk) AS predicted_rate, AVG(was_empty) AS observed_rate
        FROM ({graded}) GROUP BY store_id, store""").toPandas()
    ranked = spark.sql(f"SELECT risk, was_empty FROM ({graded})").toPandas()
    estate = by_store.drop(columns=["store_id", "scope", "model_version"]).sum()
    estate = {**estate.to_dict(), "store_id": None, "scope": "estate", "model_version": by_store.model_version.mode()[0],
              "predicted_rate": float(ranked.risk.mean()), "observed_rate": float(ranked.was_empty.mean()),
              "auc": float(roc_auc_score(ranked.was_empty, ranked.risk))}
    rows = [estate] + by_store.assign(auc=None).to_dict("records")
    for r in rows:
        r.update(graded_date=TODAY, predicted_on=TODAY - datetime.timedelta(days=1), graded_at=RUN_AT,
                 list_precision=r["listed_empty"] / r["listed"] if r["listed"] else None,
                 list_capture=r["listed_empty"] / max(r["empty"], 1))
    GRADE_COLS = [("graded_date", "DATE"), ("predicted_on", "DATE"), ("scope", "STRING"), ("store_id", "STRING"),
                  ("model_version", "STRING"), ("lines", "BIGINT"), ("empty", "BIGINT"), ("auc", "DOUBLE"),
                  ("listed", "BIGINT"), ("listed_empty", "BIGINT"), ("list_precision", "DOUBLE"), ("list_capture", "DOUBLE"),
                  ("fine_listed", "BIGINT"), ("fine_listed_empty", "BIGINT"), ("predicted_rate", "DOUBLE"),
                  ("observed_rate", "DOUBLE"), ("graded_at", "TIMESTAMP")]

    def native(v, t):
        if isinstance(v, pd.Timestamp):
            return v.to_pydatetime()
        v = v.item() if hasattr(v, "item") else v
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return int(v) if t == "BIGINT" else float(v) if t == "DOUBLE" else v

    spark.createDataFrame([tuple(native(r[c], t) for c, t in GRADE_COLS) for r in rows],
                          schema=", ".join(f"{c} {t}" for c, t in GRADE_COLS)) \
        .write.mode("overwrite").option("replaceWhere", f"graded_date = DATE'{TODAY}'").saveAsTable(GRADES)
    e = rows[0]
    print(f"Graded {TODAY} ({predicted:,} predictions): AUC {e['auc']:.3f}; watch lists {e['listed_empty']:,} of "
          f"{e['listed']:,} empty ({e['list_precision']:.1%}); looks-fine lists {e['fine_listed_empty']:,} of {e['fine_listed']:,}")
else:
    print(f"No predictions were made for {TODAY}, so there's nothing to grade yet.")

# COMMAND ----------

# MAGIC %md ## 2 · Predict tomorrow with the champion model

# COMMAND ----------

client = MlflowClient()
champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
model = mlflow.lightgbm.load_model(f"models:/{MODEL_NAME}@champion")
COLS = ", ".join(f"CAST({c} AS DOUBLE) AS {c}" for c in gr.FEATURES)
day = spark.sql(f"""SELECT store_id, upc, {COLS} FROM {FEATURE_TABLE}
    WHERE business_date = DATE'{TODAY}' AND active""").toPandas()
day["risk"] = model.predict_proba(day[gr.FEATURES])[:, 1]
day["status_today"] = np.where(day.is_gap == 1, "GAP", np.where(day.is_low == 1, "LOW", "OK"))
day["looks_fine"] = day.status_today == "OK"
day = day.sort_values(["store_id", "risk"], ascending=[True, False], kind="stable")
day["risk_rank"] = (day.groupby("store_id").cumcount() + 1).astype("int32")
day["fine_rank"] = pd.Series(np.where(day.looks_fine, day.groupby(["store_id", "looks_fine"]).cumcount() + 1, -1),
                             index=day.index).replace(-1, pd.NA).astype("Int32")
explain = day[(day.risk_rank <= REASONS_PER_STORE) | (day.fine_rank.fillna(10 ** 6) <= REASONS_PER_STORE)]
contrib = model.booster_.predict(explain[gr.FEATURES], pred_contrib=True)
day = day.join(gr.top_reasons(contrib, explain))
REASON_COLS = ["reason_1", "reason_2", "reason_3"]
day[REASON_COLS] = day[REASON_COLS].astype(object).where(day[REASON_COLS].notna(), None)
print(f"Scored {len(day):,} ranged product-locations at {day.store_id.nunique()} stores for {TOMORROW} with "
      f"{MODEL_NAME} version {champion.version}; reasons for {len(explain):,} watch-list lines")

# COMMAND ----------

# MAGIC %md ## Checks, then publish to `ml.gap_risk_scores`

# COMMAND ----------

recent = spark.sql(f"""SELECT AVG(is_gap) AS r FROM {FEATURE_TABLE}
    WHERE active AND business_date > date_sub(DATE'{TODAY}', 7) AND business_date <= DATE'{TODAY}'""").first().r
mean_risk = float(day.risk.mean())
checks = {
    "every ranged line scored": len(day) == spark.sql(
        f"SELECT COUNT(*) AS n FROM {FEATURE_TABLE} WHERE business_date = DATE'{TODAY}' AND active").first().n,
    "risk is a probability": bool(day.risk.between(0, 1).all()),
    "mean risk within 30% of the last 7 days' gap rate": abs(mean_risk - recent) <= 0.3 * recent,
    "every store has a watch list with reasons": bool((day[day.risk_rank <= gr.LIST_SIZE].groupby("store_id")
                                                       .reason_1.count() == gr.LIST_SIZE).all()),
}
for name, ok in checks.items():
    print(("PASS  " if ok else "FAIL  ") + name)
print(f"mean risk {mean_risk:.4f} vs last 7 days' rate {recent:.4f}")
assert all(checks.values()), f"Prediction checks failed: {[k for k, v in checks.items() if not v]}"

scored = spark.createDataFrame(day[["store_id", "upc", "status_today", "looks_fine", "risk", "risk_rank", "fine_rank",
                                    *REASON_COLS, "on_hand", "days_of_cover"]])
scored.createOrReplaceTempView("scored")
spark.sql(f"""CREATE TABLE IF NOT EXISTS {SCORES} (
  business_date DATE COMMENT 'Evening the prediction was made', target_date DATE COMMENT 'Morning being predicted',
  store_id STRING, store STRING, upc STRING, product STRING, category STRING, supplier STRING, depot STRING,
  status_today STRING COMMENT 'GAP, LOW or OK on the evening of the prediction',
  looks_fine BOOLEAN COMMENT 'True if the shelf was neither empty nor low',
  risk DOUBLE COMMENT 'Probability the shelf is empty on target_date for an unplanned reason',
  risk_rank INT COMMENT 'Rank within the store (1 = most at risk); the watch list is the top 25',
  fine_rank INT COMMENT 'Rank among the store''s lines that looked fine (1 = most at risk)',
  reason_1 STRING COMMENT 'Strongest reason, in plain English (watch-list lines only)', reason_2 STRING, reason_3 STRING,
  on_hand DOUBLE, days_of_cover DOUBLE, model_version STRING COMMENT 'Version of ml.gap_risk that made the prediction',
  scored_at TIMESTAMP)
  CLUSTER BY (business_date, store)
  COMMENT 'Gap-risk predictions: for every ranged product-location, the probability it is empty tomorrow morning, with reasons for each store''s watch list'""")
spark.sql(f"""
    SELECT DATE'{TODAY}' AS business_date, DATE'{TOMORROW}' AS target_date, s.store_id, st.store, s.upc, pr.product,
           pr.category, pr.supplier, st.depot, s.status_today, s.looks_fine, s.risk, CAST(s.risk_rank AS INT) AS risk_rank,
           CAST(s.fine_rank AS INT) AS fine_rank, s.reason_1, s.reason_2, s.reason_3, s.on_hand, s.days_of_cover,
           '{champion.version}' AS model_version, TIMESTAMP'{RUN_AT}' AS scored_at
    FROM scored s
    JOIN {CATALOG}.gold.dim_store st ON st.store_id = s.store_id
    JOIN {CATALOG}.gold.dim_product pr ON pr.upc = s.upc""") \
    .write.mode("overwrite").option("replaceWhere", f"business_date = DATE'{TODAY}'").saveAsTable(SCORES)
summary = {"business_date": BUSINESS_DATE, "target_date": str(TOMORROW), "model_version": str(champion.version),
           "scored": len(day), "mean_risk": round(mean_risk, 4), "graded": bool(predicted)}
print(json.dumps(summary))
dbutils.notebook.exit(json.dumps(summary))
