# Databricks notebook source
# MAGIC %md
# MAGIC # ML 1 · Train the gap-risk model
# MAGIC
# MAGIC The root-cause rules explain this morning's empty shelves. This model looks one day ahead: **which product-locations
# MAGIC will be empty tomorrow morning, for a reason nobody planned?** (A planned range exit is never predicted, because it's
# MAGIC already known.) Stores get the answer the day before, while there's still time to act.
# MAGIC
# MAGIC | Step | What happens |
# MAGIC |---|---|
# MAGIC | Data checks | Every day used reconciles with its source manifest and answer key, the calendar has no holes, and the label rate is sane |
# MAGIC | Split by time | Train on three weeks; test on the **following week, which the model never sees**. Early stopping uses the last 3 training days only |
# MAGIC | Model | LightGBM on 34 features from `ml.gap_risk_features`, built by the Lakeflow pipeline, so training and scoring share one definition |
# MAGIC | Rules to beat | "What's empty or low this morning" and "lowest stock against forecast". Both use only what a store already sees |
# MAGIC | Gates | Better than both rules by set margins, well calibrated, and no worse than the current champion on the same test week |
# MAGIC | Registry | Logged to MLflow and registered in Unity Catalog as `ml.gap_risk`. Only a version that passes every gate gets the `champion` alias, which the daily job scores with |
# MAGIC
# MAGIC Results go to MLflow and to `ops.gap_risk_evaluations`.

# COMMAND ----------

# MAGIC %pip install -q "mlflow[databricks]>=3.1" "lightgbm==4.6.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "larkwell_osa")
dbutils.widgets.text("train_days", "21")
dbutils.widgets.text("test_days", "7")
dbutils.widgets.text("negative_sample_rate", "0.03")
CATALOG = dbutils.widgets.get("catalog")
TRAIN_DAYS, TEST_DAYS = int(dbutils.widgets.get("train_days")), int(dbutils.widgets.get("test_days"))
NEG_RATE = float(dbutils.widgets.get("negative_sample_rate"))
ME = spark.sql("SELECT current_user() AS u").first().u
FEATURE_TABLE = f"{CATALOG}.ml.gap_risk_features"
MODEL_NAME = f"{CATALOG}.ml.gap_risk"
EXPERIMENT = f"/Users/{ME}/larkwell-shelf-availability-gap-risk"

import datetime
import json
import uuid

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature

import os
import sys

NOTEBOOK_DIR = os.path.dirname(dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get())
sys.path.insert(0, f"/Workspace{NOTEBOOK_DIR}")
import gap_risk as gr  # noqa: E402  ml/gap_risk.py: features, rules, metrics, reasons

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(EXPERIMENT)
client = MlflowClient()
EVALUATED_AT = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
CHECKS = []


def check(name, value, passed, note=""):
    CHECKS.append({"check": name, "value": float(value), "passed": bool(passed), "note": note})
    print(f"{'PASS' if passed else 'FAIL'}  {name:<34} {value:>14,.4f}  {note}")

# COMMAND ----------

# MAGIC %md ## Which days: three weeks to learn from, the next week to test on

# COMMAND ----------

days = [r.d for r in spark.sql(f"SELECT DISTINCT business_date AS d FROM {FEATURE_TABLE} ORDER BY d").collect()]
labelled = days[:-1]                                   # the last day's tomorrow hasn't happened yet
test = labelled[-TEST_DAYS:]
train = labelled[-(TEST_DAYS + TRAIN_DAYS):-TEST_DAYS]
assert len(train) == TRAIN_DAYS, f"need {TRAIN_DAYS + TEST_DAYS + 7} days of features, found {len(days)}"
assert days.index(train[0]) >= 6, "the first training day needs a full 7-day history behind it"
print(f"features {days[0]} to {days[-1]} | train {train[0]} to {train[-1]} | test {test[0]} to {test[-1]}")

# COMMAND ----------

# MAGIC %md ## Data checks: every day used must reconcile with its source manifest and answer key

# COMMAND ----------

used = [d for d in days if d >= train[0] - datetime.timedelta(days=6)]
calendar = [used[0] + datetime.timedelta(days=i) for i in range((used[-1] - used[0]).days + 1)]
check("calendar_days_missing", len(set(calendar) - set(used)), set(calendar) == set(used), f"{used[0]} to {used[-1]}")
per_day = {r.d: r for r in spark.sql(f"""
    SELECT business_date AS d, COUNT(*) AS rows, SUM(is_gap) AS gaps, SUM(is_low) AS lows,
           SUM(CASE WHEN active THEN 0 ELSE 1 END) AS exiting
    FROM {FEATURE_TABLE} GROUP BY business_date""").collect()}
bronze = {r.d: r.n for r in spark.sql(f"""SELECT business_date AS d, COUNT(*) AS n FROM {CATALOG}.bronze.store_stock
    GROUP BY business_date""").collect()}
bad_days = []
for d in used:
    ds = d.isoformat()
    manifest = json.load(open(f"/Volumes/{CATALOG}/raw/landing/_manifests/{ds}.json"))
    key = json.load(open(f"/Volumes/{CATALOG}/raw/answer_key/{ds}/expected_counts.json"))
    r = per_day[d]
    answers = pd.read_parquet(f"/Volumes/{CATALOG}/raw/answer_key/{ds}/exceptions.parquet", columns=["issue", "consensus_reason"])
    known_gaps = int(((answers.issue == "GAP") & (answers.consensus_reason == "KNOWN_GAP")).sum())
    ok = (r.rows == key["product_locations"] == bronze.get(d) == manifest["feeds"]["store_stock"]["rows"]
          and r.gaps == key["gaps"] - known_gaps and r.lows == key["lows"])
    if not ok:
        bad_days.append(ds)
check("days_reconciled", len(used) - len(bad_days), not bad_days,
      "rows match the manifest; gaps and lows match the answer key" + (f"; failed: {bad_days}" if bad_days else ""))

# COMMAND ----------

# MAGIC %md ## The examples: today's features, labelled with tomorrow's shelf
# MAGIC Every product-location that's ranged today is an example. Its label is 1 if the shelf is empty the next morning and
# MAGIC the line is still ranged. Training keeps every positive and a fixed 3% sample of negatives, weighted back up so the
# MAGIC model's probabilities stay calibrated. The test week is scored in full.

# COMMAND ----------

COLS = ", ".join(f"CAST(f.{c} AS DOUBLE) AS {c}" for c in gr.FEATURES)


def labelled(ds):
    """Examples for the given feature days: today's features and tomorrow's shelf (both sides filtered by date)."""
    f_days = ", ".join(f"DATE'{d}'" for d in ds)
    n_days = ", ".join(f"DATE'{d + datetime.timedelta(days=1)}'" for d in ds)
    return f"""
    SELECT f.business_date, f.store_id, f.upc, {COLS}, n.is_gap AS label
    FROM {FEATURE_TABLE} f
    JOIN {FEATURE_TABLE} n ON n.store_id = f.store_id AND n.upc = f.upc AND n.business_date = date_add(f.business_date, 1)
    WHERE f.active AND f.business_date IN ({f_days}) AND n.business_date IN ({n_days})"""


train_pdf = spark.sql(f"""SELECT * FROM ({labelled(train)})
    WHERE label = 1 OR pmod(xxhash64(store_id, upc, business_date), 100000) < {int(NEG_RATE * 100000)}""").toPandas()
train_pdf["weight"] = np.where(train_pdf.label == 1, 1.0, 1.0 / NEG_RATE)
rate = spark.sql(f"SELECT AVG(label) AS r FROM ({labelled(test)})").first().r
check("training_examples", len(train_pdf), len(train_pdf) > 1_000_000, f"{int(train_pdf.label.sum()):,} positives")
check("test_week_gap_rate", rate, 0.005 <= rate <= 0.05, "share of ranged lines empty the next morning")

# COMMAND ----------

# MAGIC %md ## Train: LightGBM, early stopping on the last 3 training days, then refit on all three weeks

# COMMAND ----------

PARAMS = dict(learning_rate=0.05, num_leaves=63, min_child_samples=200, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.8, reg_lambda=1.0, random_state=7, verbose=-1)
inner = train_pdf.business_date >= train[-3]
probe = lgb.LGBMClassifier(n_estimators=2000, **PARAMS)
probe.fit(train_pdf.loc[~inner, gr.FEATURES], train_pdf.loc[~inner, "label"], sample_weight=train_pdf.loc[~inner, "weight"],
          eval_set=[(train_pdf.loc[inner, gr.FEATURES], train_pdf.loc[inner, "label"])],
          eval_sample_weight=[train_pdf.loc[inner, "weight"]], callbacks=[lgb.early_stopping(50, verbose=False)])
N_TREES = int(probe.best_iteration_)
model = lgb.LGBMClassifier(n_estimators=N_TREES, **PARAMS)
model.fit(train_pdf[gr.FEATURES], train_pdf.label, sample_weight=train_pdf.weight)
print("trees:", N_TREES)

# COMMAND ----------

# MAGIC %md ## Test on the unseen week, day by day: the model, both rules, and the current champion

# COMMAND ----------

try:
    champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
    champion_model = mlflow.lightgbm.load_model(f"models:/{MODEL_NAME}@champion")
except Exception:
    champion, champion_model = None, None
names = ["model"] + list(gr.RULES) + (["champion"] if champion_model is not None else [])
ys, scores, fine = [], {n: [] for n in names}, []
hits = {scope: {n: [0, 0] for n in names} for scope in ("all", "looks_fine")}
daily = []
for d in test:
    day = spark.sql(labelled([d])).toPandas()
    s = {"model": model.predict_proba(day[gr.FEATURES])[:, 1], **{k: v.to_numpy() for k, v in gr.rule_scores(day).items()}}
    if champion_model is not None:
        s["champion"] = champion_model.predict_proba(day[gr.FEATURES])[:, 1]
    looks_fine = ((day.is_gap == 0) & (day.is_low == 0)).to_numpy()
    for n in names:
        for scope, mask in (("all", np.ones(len(day), bool)), ("looks_fine", looks_fine)):
            h, listed = gr.list_hits(day[mask], s[n][mask])
            hits[scope][n][0] += h
            hits[scope][n][1] += listed
        scores[n].append(s[n].astype(np.float32))
    ys.append(day.label.to_numpy(np.int8))
    fine.append(looks_fine)
    h_m, l_m = gr.list_hits(day, s["model"])
    h_t, l_t = gr.list_hits(day, s["today_rule"])
    daily.append({"features_day": str(d), "predicted_day": str(d + datetime.timedelta(days=1)), "lines": len(day),
                  "empty_next_morning": int(day.label.sum()), "model_list_precision": h_m / l_m,
                  "today_rule_list_precision": h_t / l_t})
    print(daily[-1])
y, fine = np.concatenate(ys), np.concatenate(fine)
S = {n: np.concatenate(v) for n, v in scores.items()}
results = {"all": gr.summarise(y, S, {n: tuple(v) for n, v in hits["all"].items()}, int(y.sum())),
           "looks_fine": gr.summarise(y[fine], {n: v[fine] for n, v in S.items()},
                                      {n: tuple(v) for n, v in hits["looks_fine"].items()}, int(y[fine].sum()))}
brier = float(np.mean((S["model"] - y) ** 2))
calibration_gap = abs(float(S["model"].mean()) - float(y.mean())) / float(y.mean())
deciles = pd.qcut(S["model"], 10, labels=False, duplicates="drop")
calibration = pd.DataFrame({"decile": deciles, "predicted": S["model"], "observed": y}).groupby("decile").mean().reset_index()
print(json.dumps(results, indent=1))

# COMMAND ----------

# MAGIC %md ## Gates: promote only a model that clearly beats the rules, is calibrated, and is no worse than the champion

# COMMAND ----------

A, F_ = results["all"], results["looks_fine"]
best_rule_all = max(A[r]["list_precision"] for r in gr.RULES)
best_rule_fine = max(F_[r]["list_precision"] for r in gr.RULES)
GATES = [
    ("auc_all", A["model"]["auc"], A["model"]["auc"] >= 0.85 and A["model"]["auc"] >= A["today_rule"]["auc"] + 0.05,
     "AUC at least 0.85, and 0.05 above the today rule"),
    ("watch_list_precision_all", A["model"]["list_precision"], A["model"]["list_precision"] >= 1.15 * best_rule_all,
     f"top {gr.LIST_SIZE} per store: at least 1.15x the better rule ({best_rule_all:.1%})"),
    ("watch_list_precision_looks_fine", F_["model"]["list_precision"], F_["model"]["list_precision"] >= 2 * best_rule_fine,
     f"lines that look fine today, top {gr.LIST_SIZE} per store: at least 2x the better rule ({best_rule_fine:.1%})"),
    ("calibration_gap", calibration_gap, calibration_gap <= 0.15, "mean predicted risk within 15% of the observed rate"),
    ("data_checks", sum(c["passed"] for c in CHECKS), all(c["passed"] for c in CHECKS), "every data check above passed"),
]
if champion_model is not None:
    GATES.append(("no_worse_than_champion", A["model"]["auc"] - A["champion"]["auc"],
                  A["model"]["auc"] >= A["champion"]["auc"] - 0.005,
                  f"AUC within 0.005 of champion version {champion.version} on the same test week"))
PROMOTE = all(passed for _, _, passed, _ in GATES)
for name, value, passed, note in GATES:
    print(f"{'PASS' if passed else 'FAIL'}  {name:<34} {value:>8.4f}  {note}")
print("Promote to champion:", PROMOTE)

# COMMAND ----------

# MAGIC %md ## Log to MLflow and register in Unity Catalog

# COMMAND ----------

importance = pd.DataFrame({"feature": gr.FEATURES, "gain": model.booster_.feature_importance("gain")})
importance["share"] = (importance.gain / importance.gain.sum()).round(4)
importance = importance.sort_values("share", ascending=False)
example = train_pdf[gr.FEATURES].head(5)
with mlflow.start_run(run_name=f"gap-risk {train[0]} to {train[-1]}") as run:
    mlflow.log_params({"train_from": str(train[0]), "train_to": str(train[-1]), "test_from": str(test[0]),
                       "test_to": str(test[-1]), "features": len(gr.FEATURES), "trees": N_TREES,
                       "negative_sample_rate": NEG_RATE, "list_size": gr.LIST_SIZE, "feature_table": FEATURE_TABLE,
                       **{f"lgbm_{k}": v for k, v in PARAMS.items()}})
    mlflow.log_input(mlflow.data.from_pandas(train_pdf[gr.FEATURES + ["label"]].head(100_000), source=FEATURE_TABLE,
                                             name="gap_risk_training_sample"), context="training")
    for scope, res in results.items():
        for scorer, m in res.items():
            mlflow.log_metrics({f"{scope}.{scorer}.{k}": v for k, v in m.items()})
    mlflow.log_metrics({"brier": brier, "calibration_gap": calibration_gap, "test_rate": float(y.mean())})
    mlflow.log_table(pd.DataFrame(daily), "test_week_by_day.json")
    mlflow.log_table(calibration, "calibration_by_decile.json")
    mlflow.log_table(importance, "feature_importance.json")
    mlflow.log_table(pd.DataFrame(CHECKS), "data_checks.json")
    mlflow.log_table(pd.DataFrame(GATES, columns=["gate", "value", "passed", "rule"]), "gates.json")
    info = mlflow.lightgbm.log_model(model, name="model", input_example=example,
                                     signature=infer_signature(example, model.predict_proba(example)[:, 1]),
                                     registered_model_name=MODEL_NAME)
VERSION = str(info.registered_model_version)
client.update_registered_model(MODEL_NAME, description=(
    "Larkwell Foods (fictitious) gap-risk model: the probability that a ranged product-location is empty tomorrow "
    "morning for an unplanned reason, from ml.gap_risk_features. Trained by ml/01_train_gap_risk.py; scored daily by "
    "ml/02_score_gap_risk.py. The champion alias is moved only by a version that passes every gate. Synthetic data."))
client.update_model_version(MODEL_NAME, VERSION, description=(
    f"Trained on {train[0]} to {train[-1]}, tested on the unseen week {test[0]} to {test[-1]}. "
    f"AUC {A['model']['auc']:.3f} (today rule {A['today_rule']['auc']:.3f}); top-{gr.LIST_SIZE} watch list "
    f"{A['model']['list_precision']:.0%} empty next morning (today rule {A['today_rule']['list_precision']:.0%}); "
    f"lines that look fine today {F_['model']['list_precision']:.1%} (lowest-cover rule "
    f"{F_['lowest_cover_rule']['list_precision']:.1%}). Gates {'passed' if PROMOTE else 'NOT passed'}."))
for k, v in {"train_window": f"{train[0]}..{train[-1]}", "test_window": f"{test[0]}..{test[-1]}",
             "test_auc": f"{A['model']['auc']:.4f}", "watch_list_precision": f"{A['model']['list_precision']:.4f}",
             "gates_passed": str(PROMOTE).lower(), "mlflow_run_id": run.info.run_id}.items():
    client.set_model_version_tag(MODEL_NAME, VERSION, k, v)
client.set_registered_model_alias(MODEL_NAME, "champion" if PROMOTE else "challenger", VERSION)
print(f"Registered {MODEL_NAME} version {VERSION} as {'champion' if PROMOTE else 'challenger'} | MLflow run {run.info.run_id}")

# COMMAND ----------

# MAGIC %md ## Publish the evaluation to `ops.gap_risk_evaluations`

# COMMAND ----------

rows = []
for scope, res in results.items():
    for metric in ("auc", "average_precision", "list_precision", "list_capture"):
        rows.append({"metric": f"{scope}.{metric}", **{n: float(res[n][metric]) for n in names}})
rows += [{"metric": "brier", "model": brier}, {"metric": "calibration_gap", "model": calibration_gap}]
rows += [{"metric": f"check.{c['check']}", "model": c["value"], "check_note": c["note"], "check_passed": c["passed"]} for c in CHECKS]
rows += [{"metric": f"gate.{g}", "model": float(v), "check_note": note, "check_passed": bool(ok)} for g, v, ok, note in GATES
         if g in ("no_worse_than_champion", "data_checks")]
ev = pd.DataFrame(rows)
for n in ("model", "today_rule", "lowest_cover_rule", "champion"):
    if n not in ev:
        ev[n] = np.nan
gate_of = {g[0]: g for g in GATES}
metric_gate = {"all.auc": "auc_all", "all.list_precision": "watch_list_precision_all",
               "looks_fine.list_precision": "watch_list_precision_looks_fine", "calibration_gap": "calibration_gap"}
ev["gate"] = [gate_of[metric_gate[m]][3] if m in metric_gate else (n if isinstance(n, str) else None)
              for m, n in zip(ev.metric, ev.check_note)]
ev["passed"] = [bool(gate_of[metric_gate[m]][2]) if m in metric_gate else (bool(p) if isinstance(p, (bool, np.bool_)) else None)
                for m, p in zip(ev.metric, ev.check_passed)]
ev = ev.assign(evaluation_id=str(uuid.uuid4()), evaluated_at=EVALUATED_AT, mlflow_run_id=run.info.run_id,
               model_version=VERSION, champion_version=champion.version if champion else None, promoted=PROMOTE,
               train_from=train[0], train_to=train[-1], test_from=test[0], test_to=test[-1], trees=N_TREES)
spark.sql(f"""CREATE TABLE IF NOT EXISTS {CATALOG}.ops.gap_risk_evaluations (
  evaluation_id STRING, evaluated_at TIMESTAMP, mlflow_run_id STRING, model_version STRING, champion_version STRING,
  promoted BOOLEAN, train_from DATE, train_to DATE, test_from DATE, test_to DATE, trees INT, metric STRING,
  model DOUBLE, today_rule DOUBLE, lowest_cover_rule DOUBLE, champion DOUBLE, gate STRING, passed BOOLEAN)
  COMMENT 'Every training run of the gap-risk model: test-week metrics for the model, the two rules it must beat and the champion, with the promotion gates'""")
cols = ["evaluation_id", "evaluated_at", "mlflow_run_id", "model_version", "champion_version", "promoted", "train_from",
        "train_to", "test_from", "test_to", "trees", "metric", "model", "today_rule", "lowest_cover_rule", "champion",
        "gate", "passed"]
SCHEMA = ("evaluation_id STRING, evaluated_at TIMESTAMP, mlflow_run_id STRING, model_version STRING, champion_version STRING, "
          "promoted BOOLEAN, train_from DATE, train_to DATE, test_from DATE, test_to DATE, trees INT, metric STRING, "
          "model DOUBLE, today_rule DOUBLE, lowest_cover_rule DOUBLE, champion DOUBLE, gate STRING, passed BOOLEAN")


def native(v):
    """Plain Python values for Spark: pandas timestamps and numpy scalars unwrapped, NaN as NULL."""
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    v = v.item() if hasattr(v, "item") else v
    return None if isinstance(v, float) and np.isnan(v) else v


records = [tuple(native(r[c]) for c in cols) for r in ev[cols].to_dict("records")]
spark.createDataFrame(records, schema=SCHEMA).write.mode("append").saveAsTable(f"{CATALOG}.ops.gap_risk_evaluations")
spark.sql(f"""CREATE TABLE IF NOT EXISTS {CATALOG}.ops.gap_risk_feature_importance (
  evaluation_id STRING, mlflow_run_id STRING, model_version STRING, feature STRING, gain_share DOUBLE)
  COMMENT 'What each gap-risk model version learned to rely on: each feature''s share of the trees'' total gain'""")
spark.createDataFrame([(ev.evaluation_id[0], run.info.run_id, VERSION, f, float(g)) for f, g in zip(importance.feature, importance.share)],
                      schema="evaluation_id STRING, mlflow_run_id STRING, model_version STRING, feature STRING, gain_share DOUBLE") \
    .write.mode("append").saveAsTable(f"{CATALOG}.ops.gap_risk_feature_importance")
summary = {"model_version": VERSION, "promoted": PROMOTE, "mlflow_run_id": run.info.run_id,
           "auc": round(A["model"]["auc"], 4), "watch_list_precision": round(A["model"]["list_precision"], 4)}
print(json.dumps(summary))
assert PROMOTE or champion is not None, "No version has passed the gates yet, so there is nothing to score with"
dbutils.notebook.exit(json.dumps(summary))
