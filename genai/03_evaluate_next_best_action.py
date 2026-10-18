# Databricks notebook source
# MAGIC %md
# MAGIC # 3 · Evaluate the next best action (MLflow GenAI evaluation)
# MAGIC
# MAGIC The Shelf Scan's next best action is where an LLM writes advice for a store colleague, so it gets a formal evaluation.
# MAGIC It tests **the exact prompt the app uses** (`app/nba.py`), and scores exactly the text a colleague sees (after `nba.clean`),
# MAGIC on real exceptions from today's gold table: 6 per root cause, 48 in all.
# MAGIC
# MAGIC | Scorer | Type | What it checks | Pass threshold |
# MAGIC |---|---|---|---|
# MAGIC | `numbers_grounded` | Code | Every number in the advice appears in the facts given (no rounding or invented numbers) | 98% |
# MAGIC | `follows_playbook` | Code | The advice contains the playbook action for the root cause | 95% |
# MAGIC | `no_contradiction` | Code | No forbidden advice, e.g. "chase the supplier" for a planned range exit | 100% |
# MAGIC | `no_internal_codes` | Code | No codes such as SUPPLIER_SHORT | 100% |
# MAGIC | `units_only` | Code | No invented units such as cases or boxes | 100% |
# MAGIC | `concise` | Code | At most 3 sentences and 75 words | 90% |
# MAGIC | `plain_english` | LLM judge | Plain, friendly English for a store colleague: tone and wording only (codes and the action itself are checked exactly by `no_internal_codes` and `follows_playbook`) | 90% |
# MAGIC | `consistent_with_playbook` | LLM judge | Doesn't contradict the recommended action | 95% |
# MAGIC
# MAGIC Before scoring, each LLM judge is **calibrated**: it grades a fixed set of hand-labelled answers, good and deliberately bad,
# MAGIC and must agree with every label. A judge that passes bad advice, or fails good advice, can't be trusted to gate the job.
# MAGIC The judges run on a different model family (GPT-5.5) from the one that writes the advice (Claude Sonnet 4.5), so no model grades its own family's work.
# MAGIC
# MAGIC Results are logged to an MLflow experiment (with a trace per call) and written to `ops.genai_eval_results`.

# COMMAND ----------

# MAGIC %pip install -q "mlflow[databricks]>=3.1" openai httpx "databricks-sdk>=0.81"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "larkwell_osa")
dbutils.widgets.text("llm_endpoint", "databricks-claude-sonnet-4-5")
dbutils.widgets.text("judge_model", "databricks:/databricks-gpt-5-5")
dbutils.widgets.text("app_source", "")
dbutils.widgets.text("cases_per_reason", "6")
CATALOG = dbutils.widgets.get("catalog")
ENDPOINT = dbutils.widgets.get("llm_endpoint")
JUDGE_MODEL = dbutils.widgets.get("judge_model")
PER_REASON = int(dbutils.widgets.get("cases_per_reason"))
ME = spark.sql("SELECT current_user() AS u").first().u
APP_SOURCE = dbutils.widgets.get("app_source") or f"/Workspace/Users/{ME}/larkwell-shelf-availability/app"
EXPERIMENT = f"/Users/{ME}/larkwell-shelf-availability-next-best-action-eval"

import datetime
import json
import re
import sys

import mlflow
import pandas as pd
from databricks.sdk import WorkspaceClient
from mlflow.entities import Feedback
from mlflow.genai.scorers import Guidelines, scorer

sys.path.insert(0, APP_SOURCE)
import nba  # noqa: E402  the app's own prompt, playbook and fallback

mlflow.set_experiment(EXPERIMENT)
mlflow.openai.autolog()
client = WorkspaceClient().serving_endpoints.get_open_ai_client()
print("Evaluating prompt", nba.PROMPT_VERSION, "on", ENDPOINT, "| judges on", JUDGE_MODEL, "| experiment", EXPERIMENT)

# COMMAND ----------

# MAGIC %md ## Test cases: real exceptions from today's gold table

# COMMAND ----------

COLUMNS = ("store, upc, product, category, issue, low_issue, consensus_reason, supplier, depot, supplier_short_qty, "
           "scarcity_qty, waste_qty, under_forecast_qty, under_space_qty, stockfile_adjustment_qty, on_hand_units, "
           "presentation_min_units, forecast_units")
cases = spark.sql(f"""
    SELECT {COLUMNS} FROM (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY consensus_reason ORDER BY xxhash64(store, upc)) AS rn
      FROM {CATALOG}.gold.product_location_status WHERE issue <> 'NO_ISSUE')
    WHERE rn <= {PER_REASON} ORDER BY consensus_reason, rn""").toPandas()


def as_app_event(row):
    """The app passes values as strings (the shape the SQL API and Lakebase layer return); do the same."""
    out = {}
    for k, v in row.items():
        if v is None or (isinstance(v, float) and v != v):
            out[k] = None
        elif isinstance(v, bool):
            out[k] = "true" if v else "false"
        elif isinstance(v, float):
            out[k] = str(v)
        else:
            out[k] = str(v)
    return out


data, case_meta = [], {}
for _, r in cases.iterrows():
    event = as_app_event(r.to_dict())
    facts = nba.facts(event, event["store"])          # exactly what the app puts in front of the model
    data.append({"inputs": {"store": event["store"], "facts": facts},
                 "expectations": {"root_cause": event["consensus_reason"], "product": event.get("product") or "",
                                  "allowed_numbers": sorted(nba.allowed_numbers(event, event["store"]))}})
    case_meta[facts] = {"root_cause": event["consensus_reason"], "store": event["store"], "upc": event["upc"],
                        "product": event.get("product")}
first = as_app_event(cases.iloc[0].to_dict())
assert nba.build_messages(first, first["store"]) == [{"role": "system", "content": nba.SYSTEM_PROMPT},
    {"role": "user", "content": "Facts:\n" + data[0]["inputs"]["facts"]}], "evaluation must use the app's exact prompt"
print(len(data), "cases:", cases.consensus_reason.value_counts().to_dict())

# COMMAND ----------

# MAGIC %md ## The system under test and the scorers

# COMMAND ----------

@mlflow.trace(span_type="CHAIN")
def predict_fn(store, facts):
    # Same messages as nba.build_messages(event, store): the system prompt, then "Facts:" and the facts.
    messages = [{"role": "system", "content": nba.SYSTEM_PROMPT}, {"role": "user", "content": "Facts:\n" + facts}]
    resp = client.chat.completions.create(model=ENDPOINT, messages=messages, max_tokens=220)
    content = resp.choices[0].message.content
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return nba.clean(content)        # exactly what the app shows the colleague


PLAYBOOK_TERMS = {  # the advice must contain at least one of these for the root cause
    "KNOWN_GAP": ["no action", "planned", "range exit", "deliberate"],
    "SCARCITY": ["alternative"],
    "SUPPLIER_SHORT": ["shortage query", "depot"],
    "ORDER_DELIVERY_BLOCK": ["release", "speed it up", "expedite", "unblock", "blocked order"],
    "STOCKFILE_ADJUSTMENT": ["count"],
    "WASTE": ["date code", "handling", "order quantity"],
    "UNDER_FORECAST": ["order"],
    "INVESTIGATE": ["analyst", "investigat"],
}
FORBIDDEN = {  # advice that would contradict the playbook, unless negated ("don't chase the supplier")
    "KNOWN_GAP": [r"chase", r"shortage query", r"re-?order"],
    "SCARCITY": [r"chase", r"shortage query"],
    "ORDER_DELIVERY_BLOCK": [r"place a (new|second) order", r"re-?order"],
}
NEGATION = re.compile(r"\b(don't|do not|no need to|never|not|without|isn't|no action)\b", re.I)
CODES = re.compile(r"\b(KNOWN_GAP|SCARCITY|SUPPLIER_SHORT|ORDER_DELIVERY_BLOCK|STOCKFILE_ADJUSTMENT|UNDER_FORECAST|"
                   r"INVESTIGATE|WASTE|SALES_LOW|SPACE_LOW|consensus_reason)\b")
UNITS = re.compile(r"\b(cases?|boxes|crates?|trays?|cartons?)\b", re.I)


@scorer
def numbers_grounded(outputs, expectations):
    allowed = set(expectations["allowed_numbers"])
    used = set(re.findall(r"\d+(?:\.\d+)?", outputs or ""))
    extra = sorted(used - allowed)
    return Feedback(value=not extra, rationale="all numbers come from the facts" if not extra else f"not in the facts: {extra}")


@scorer
def follows_playbook(outputs, expectations):
    reason = expectations["root_cause"]
    hit = [t for t in PLAYBOOK_TERMS[reason] if t in (outputs or "").lower()]
    return Feedback(value=bool(hit), rationale=f"found {hit}" if hit else f"none of {PLAYBOOK_TERMS[reason]}")


@scorer
def no_contradiction(outputs, expectations):
    text = outputs or ""
    for pattern in FORBIDDEN.get(expectations["root_cause"], []):
        for m in re.finditer(pattern, text, re.I):
            sentence_start = max(text.rfind(c, 0, m.start()) for c in ".!?\n") + 1   # negation anywhere earlier in the sentence
            if not NEGATION.search(text[sentence_start:m.start()]):
                return Feedback(value=False, rationale=f"says '{m.group(0)}' without negation")
    return Feedback(value=True, rationale="no contradicting advice")


@scorer
def no_internal_codes(outputs):
    m = CODES.search(outputs or "")
    return Feedback(value=m is None, rationale="plain words only" if m is None else f"uses code {m.group(0)}")


@scorer
def units_only(outputs, expectations):
    product = (expectations.get("product") or "").lower()
    bad = [u for u in UNITS.findall(outputs or "") if u.lower() not in product]
    return Feedback(value=not bad, rationale="only 'units'" if not bad else f"invented units: {bad}")


@scorer
def concise(outputs):
    text = (outputs or "").strip()
    sentences = len([s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()])
    words = len(text.split())
    return Feedback(value=sentences <= 3 and words <= 75, rationale=f"{sentences} sentences, {words} words")


# The judge assesses language only. Whether the advice gives the right action is checked exactly by follows_playbook.
# Internal codes are checked exactly by no_internal_codes, so the judge assesses tone and plainness only.
# Both judges are told what not to judge. Earlier wordings marked correct advice down for not naming the store, for a
# depot name, and for leaving out a "don't" instruction (leaving something out isn't contradicting it). The default
# judge model still missed that last rule on real cases, so both judges run on a model that follows it (see calibration).
plain_english = Guidelines(name="plain_english", guidelines=[
    "Judge only how the response is written, not which facts it includes. Proper names are never jargon: the names "
    "of stores, products, suppliers and depots (for example 'Merseyvale DC' or 'Oldcastle Confectionery') are fine, "
    "and so are everyday retail words such as shelf, delivery, depot, stock file, phantom stock, allocation, range "
    "and order. The response doesn't need to mention any particular name or word. It passes if it is plain, "
    "friendly British English that a store colleague would understand at a glance on a handheld device. It fails "
    "only if it uses jargon or corporate or technical language, reads like a system message or a list of codes, or "
    "is curt or rude."], model=JUDGE_MODEL)
consistent = Guidelines(name="consistent_with_playbook", guidelines=[
    "The response must not contradict the 'Recommended action' line given in the request: it must not tell the "
    "colleague to do something that line rules out, or to skip what it asks for. Leaving out part of the "
    "recommended action, such as one of its 'don't' instructions, is not a contradiction."], model=JUDGE_MODEL)
SCORERS = [numbers_grounded, follows_playbook, no_contradiction, no_internal_codes, units_only, concise,
           plain_english, consistent]
THRESHOLDS = {"numbers_grounded": 0.98, "follows_playbook": 0.95, "no_contradiction": 1.0, "no_internal_codes": 1.0,
              "units_only": 1.0, "concise": 0.90, "plain_english": 0.90, "consistent_with_playbook": 0.95}

# COMMAND ----------

# MAGIC %md ## Calibrate the judges against hand-labelled answers

# COMMAND ----------

# Fixed facts, built with the app's own facts(), and answers labelled by hand. The bad answers are the failures each
# judge exists to catch: jargon, a curt tone, a system message, and advice that contradicts the playbook.
CAL_EVENTS = {
    "uf": {"store": "Marlow", "product": "Black Bean Sauce 350g", "issue": "LOW", "low_issue": "SALES_LOW",
           "consensus_reason": "UNDER_FORECAST", "under_forecast_qty": "4", "on_hand_units": "2", "presentation_min_units": "6"},
    "sfa": {"store": "St Andrews Local", "product": "Veggie Crisps 100g Family Pack", "issue": "GAP",
            "consensus_reason": "STOCKFILE_ADJUSTMENT", "stockfile_adjustment_qty": "4"},
    "sc": {"store": "Aviemore", "product": "Sour Cream 150ml", "issue": "GAP", "consensus_reason": "SCARCITY",
           "scarcity_qty": "9", "supplier": "Fernleigh Cheesemakers"},
    "ss": {"store": "Covent Garden", "product": "Milk Chocolate Buttons 70g", "issue": "GAP", "consensus_reason": "SUPPLIER_SHORT",
           "supplier_short_qty": "6", "supplier": "Oldcastle Confectionery", "depot": "Merseyvale DC"},
    "kg": {"store": "Marlow", "product": "Christmas Pudding 454g", "issue": "GAP", "consensus_reason": "KNOWN_GAP"},
    "wa": {"store": "Prestwick Forecourt", "product": "Pork Mince 800g", "issue": "GAP", "consensus_reason": "WASTE",
           "waste_qty": "7"},
    "odb": {"store": "Covent Garden", "product": "Chicken Tikka Masala 400g", "issue": "GAP",
            "consensus_reason": "ORDER_DELIVERY_BLOCK", "depot": "Merseyvale DC"},
}
CALIBRATION = [  # (judge, [(event, answer, the human label)])
    (plain_english, [
        ("uf", "This sauce sold 4 units more than expected, so the shelf ran low even though it was stocked correctly. "
               "Order extra units today and let the ordering team know it's selling faster than forecast.", "yes"),
        ("sfa", "The system thought there were 4 units in store so it didn't order more, but they weren't actually here. "
                "Count the shelf and stockroom, then correct the stock file so automatic ordering can restart.", "yes"),
        ("sc", "The shelf is empty because there's a market-wide shortage, which means 9 units were cut from your "
               "delivery. Fill the space with an approved alternative line.", "yes"),
        ("ss", "The last delivery from Merseyvale DC came in 6 units short, so the shelf is empty. Raise a shortage query "
               "with the depot for the missing units and check when the next delivery is due.", "yes"),
        ("uf", "Demand variance of 4 units against the statistical forecast has driven a sub-presentation-minimum "
               "inventory position; escalate a replenishment parameter recalibration request to the demand planning "
               "function.", "no"),
        ("sfa", "Your stock file is wrong again. Count it properly this time and fix it.", "no"),
        ("sc", "STATUS: GAP. CAUSE: MARKET SHORTAGE. QTY CUT: 9. ACTION: SUBSTITUTE APPROVED ALTERNATIVE. END.", "no"),
        ("ss", "An inbound fulfilment non-conformance of 6 units has been identified against the ASN; initiate a "
               "supplier-short exception workflow via the DC escalation matrix.", "no"),
        ("uf", "# Response for Shelf Scan Device\n\nThis sauce sold 4 units more than expected, so the shelf ran low. "
               "Order extra units today and let the ordering team know.", "no"),
    ]),
    (consistent, [
        ("kg", "This line is being taken out of the range, so the gap is planned. No action is needed: don't chase the "
               "supplier or reorder.", "yes"),
        ("kg", "The shelf is empty, so chase the supplier today and reorder enough units to fill it.", "no"),
        ("sc", "The shelf is empty because there's a market-wide shortage, which means 9 units were cut from your "
               "delivery. Fill the space with an approved alternative line.", "yes"),
        ("sc", "There's a shortage, so raise a shortage query and chase Fernleigh Cheesemakers for the 9 missing units.", "no"),
        ("odb", "The order for this line is blocked at Merseyvale DC, so nothing has arrived. Ask the depot to release "
                "the blocked order or speed it up, rather than placing a second one.", "yes"),
        ("odb", "Nothing has arrived, so place a second order for this line today to be safe.", "no"),
        ("odb", "The order for this line is blocked at Merseyvale DC, so nothing can reach the shelf. Ask the depot to "
                "release the blocked order or speed it up.", "yes"),
        ("ss", "The last delivery came in 6 units short, but there's nothing you need to do about it.", "no"),
        ("sc", "There's a market-wide shortage of Sour Cream 150ml, so your allocation was cut by 9 units. Fill the space "
               "with an approved alternative line.", "yes"),
        ("wa", "The shelf is empty because 7 units were written off as waste. Check the date codes and handling, then ask "
               "your manager to review the order quantity for this short-life line.", "yes"),
    ]),
]
cal_rows = []
for judge, items in CALIBRATION:
    for key, answer, label in items:
        e = CAL_EVENTS[key]
        fb = judge(inputs={"store": e["store"], "facts": nba.facts(e, e["store"])}, outputs=answer)
        verdict = str(fb.value).lower()
        cal_rows.append({"judge": judge.name, "answer": answer, "label": label, "verdict": verdict,
                         "agrees": verdict == label, "rationale": fb.rationale})
calibration = pd.DataFrame(cal_rows)
# Published with the results; any disagreement fails the job at the end, because the judges then can't be trusted.
CALIBRATION_SUMMARY = [{"metric": f"judge_calibration_{name}", "value": round(float(g.agrees.mean()), 4), "threshold": 1.0,
                        "passed": bool(g.agrees.all())} for name, g in calibration.groupby("judge")]
print(calibration[["judge", "label", "verdict", "agrees"]].to_string(index=False))

# COMMAND ----------

# MAGIC %md ## Run the evaluation

# COMMAND ----------

with mlflow.start_run(run_name=f"next-best-action {nba.PROMPT_VERSION}") as run:
    mlflow.log_params({"prompt_version": nba.PROMPT_VERSION, "endpoint": ENDPOINT, "judge_model": JUDGE_MODEL, "cases": len(data)})
    result = mlflow.genai.evaluate(data=data, predict_fn=predict_fn, scorers=SCORERS)
    mlflow.log_metrics({s["metric"]: s["value"] for s in CALIBRATION_SUMMARY})
    mlflow.log_table(calibration, artifact_file="judge_calibration.json")
RUN_ID = run.info.run_id

# Per-case results, from the traces the evaluation recorded: one trace per case, carrying every scorer's assessment.
SCORER_NAMES = list(THRESHOLDS)


def _as_dict(x):
    if isinstance(x, dict):
        return x
    try:
        return json.loads(x)
    except Exception:  # noqa: BLE001
        return {}


traces = mlflow.search_traces(run_id=result.run_id)
rows = []
for _, t in traces.iterrows():
    req = _as_dict(t["request"])
    for key in ("inputs", "request"):
        if isinstance(req.get(key), dict):
            req = req[key]
    meta = case_meta.get(req.get("facts"), {})
    resp = t["response"]
    if isinstance(resp, str) and resp.startswith('"'):
        resp = json.loads(resp)
    rec = {**{k: meta.get(k) for k in ("root_cause", "store", "upc", "product")},
           "advice": resp if isinstance(resp, str) else json.dumps(resp)}
    for a in (t["assessments"] if isinstance(t["assessments"], list) else []):
        name = getattr(a, "name", None) or (a.get("assessment_name") if isinstance(a, dict) else None)
        if name not in SCORER_NAMES:
            continue
        rec[name] = getattr(a, "value", None) if not isinstance(a, dict) else (a.get("feedback") or {}).get("value")
        rec[name + "_why"] = getattr(a, "rationale", None) if not isinstance(a, dict) else a.get("rationale")
    if any(n in rec for n in SCORER_NAMES):
        rows.append(rec)
per_case = pd.DataFrame(rows).dropna(subset=["upc"]).drop_duplicates(subset=["store", "upc"])
print(len(traces), "traces,", len(per_case), "scored cases; aggregate metrics from MLflow:", json.dumps(result.metrics)[:600])


def rate(col):
    v = per_case[col].map(lambda x: str(x).lower() in ("true", "yes", "pass", "1"))
    return round(float(v.mean()), 4)


summary = [{"metric": m, "value": rate(m), "threshold": thr, "passed": rate(m) >= thr} for m, thr in THRESHOLDS.items()
           if m in per_case.columns] + CALIBRATION_SUMMARY
print(pd.DataFrame(summary).to_string(index=False))

# COMMAND ----------

# MAGIC %md ## Publish the results to Unity Catalog

# COMMAND ----------

now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
meta = {"evaluated_at": now, "mlflow_run_id": result.run_id, "prompt_version": nba.PROMPT_VERSION, "model": ENDPOINT,
        "judge_model": JUDGE_MODEL, "cases": len(per_case)}
spark.createDataFrame(pd.DataFrame([{**meta, **s} for s in summary])).write.mode("append").option(
    "mergeSchema", "true").saveAsTable(f"{CATALOG}.ops.genai_eval_results")
spark.createDataFrame(per_case.assign(**{k: str(v) for k, v in meta.items()}).astype(str)).write.mode("append").option(
    "mergeSchema", "true").saveAsTable(f"{CATALOG}.ops.genai_eval_cases")
spark.createDataFrame(calibration.assign(**{k: str(v) for k, v in meta.items()}).astype(str)).write.mode("append").option(
    "mergeSchema", "true").saveAsTable(f"{CATALOG}.ops.genai_judge_calibration")
failed = [s["metric"] for s in summary if not s["passed"]]
out = {"mlflow_run_id": result.run_id, "prompt_version": nba.PROMPT_VERSION, "cases": len(per_case),
       "metrics": {s["metric"]: s["value"] for s in summary}, "failed": failed}
print(json.dumps(out, indent=2))
assert not failed, f"Below threshold: {failed}"
dbutils.notebook.exit(json.dumps(out))
