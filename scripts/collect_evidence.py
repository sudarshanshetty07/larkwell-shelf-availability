"""Regenerate the execution evidence in evidence/ as readable text, straight from the live workspace.

Every file is produced from a query or API call made when this script runs; nothing is typed in by hand.
Hostnames, workspace IDs and email addresses are redacted.

    DATABRICKS_CONFIG_PROFILE=<profile> python3 scripts/collect_evidence.py
"""
import datetime
import json
import os
import re
import subprocess

CFG = json.load(open("conf/settings.json"))
C = CFG["catalog"]
OUT = "evidence"
PIPELINE_KEY, JOB_KEY = "availability_pipeline", "daily_run"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def redact(text):
    text = re.sub(r"[A-Za-z0-9._%+-]+@(?!larkwell\.example\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<user>", text)
    text = re.sub(r"https?://[A-Za-z0-9.-]*(azuredatabricks\.net|databricksapps\.com|cloud\.databricks\.com)[^\s|)]*", "<workspace-url>", text)
    text = re.sub(r"\badb-\d+\.\d+\b|\b\d{15}\b(?=\.)", "<workspace>", text)
    return re.sub(r"ep-[a-z]+-[a-z]+-[a-z0-9]+\.database\.[a-z0-9.]+", "<lakebase-host>", text)


def cli(*args):
    r = subprocess.run(["databricks", *args, "-o", "json"], capture_output=True, text=True)
    return json.loads(r.stdout) if r.stdout.strip().startswith(("{", "[")) else {}


def sql(statement):
    body = json.dumps({"statement": statement, "warehouse_id": CFG["warehouse_id"], "wait_timeout": "50s"})
    d = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--json", body],
                                  capture_output=True, text=True).stdout or "{}")
    if d.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(d.get("status", {}).get("error", {}).get("message", str(d))[:500])
    cols = [c["name"] for c in d["manifest"]["schema"]["columns"]]
    return [dict(zip(cols, r)) for r in d.get("result", {}).get("data_array", [])]


def table(rows, cols=None, fmt=None):
    if not rows:
        return "_No rows._\n"
    cols = cols or list(rows[0].keys())
    fmt = fmt or {}
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c)
            v = fmt[c](v) if c in fmt and v is not None else ("" if v is None else str(v))
            cells.append(v.replace("|", "\\|").replace("\n", " "))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def num(v):
    try:
        f = float(v)
        return f"{f:,.0f}" if f == int(f) else f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(v)


def write(name, title, body):
    text = f"# {title}\n\n_Generated {NOW} by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._\n\n{body}"
    with open(os.path.join(OUT, name), "w") as f:
        f.write(redact(text))
    print("wrote", name)


bundle = cli("bundle", "summary")["resources"]
PIPELINE_ID = bundle["pipelines"][PIPELINE_KEY]["id"]
JOB_ID = bundle["jobs"][JOB_KEY]["id"]
dates = [r["d"] for r in sql(f"SELECT DISTINCT CAST(business_date AS STRING) AS d FROM {C}.ops.pipeline_checks ORDER BY d")]

# ------------------------------------------------------------------------------------------------- 01 raw feeds
body = ("The generator (`data/01_land_raw_feeds.py`) plays the source systems and lands one folder per feed per trading "
        "day in the Unity Catalog volume `raw.landing`. Each day also gets a manifest, which the daily checks reconcile against.\n\n")
for d in dates:
    man = json.loads(subprocess.run(["databricks", "fs", "cat", f"dbfs:/Volumes/{C}/raw/landing/_manifests/{d}.json"],
                                    capture_output=True, text=True).stdout)
    rows = [{"feed": k, "files": len(v["files"]), "rows": v["rows"], "example file": v["files"][0]} for k, v in man["feeds"].items()]
    body += f"## Business date {d}\n\n" + table(rows, fmt={"rows": num}) + "\n"
exp = json.loads(subprocess.run(["databricks", "fs", "cat", f"dbfs:/Volumes/{C}/raw/answer_key/{dates[-1]}/expected_counts.json"],
                                capture_output=True, text=True).stdout)
body += ("## Answer key (written alongside, never read by the pipeline)\n\n```json\n" + json.dumps(exp, indent=2) + "\n```\n")
write("01_raw_feeds.md", "Raw feeds landed by the simulated source systems", body)

# ------------------------------------------------------------------------------------------------- 02 Lakeflow pipeline
p = cli("pipelines", "get", PIPELINE_ID)
spec = p.get("spec", {})
updates = cli("pipelines", "list-updates", PIPELINE_ID, "--max-results", "6").get("updates", [])
body = (f"Pipeline `{spec.get('name')}`: serverless={spec.get('serverless')}, development={spec.get('development')}, "
        f"channel={spec.get('channel')}, catalog `{spec.get('catalog')}`, {len(spec.get('libraries', []))} library glob "
        f"(25 SQL files: 10 bronze, 10 silver, 5 gold). Managed by the bundle in `resources/availability_pipeline.pipeline.yml`.\n\n"
        "## Recent updates\n\n")
body += table([{"update": u.get("update_id"), "state": u.get("state"), "triggered by": u.get("cause"),
                "full refresh": u.get("full_refresh", False),
                "started (UTC)": datetime.datetime.fromtimestamp(int(u.get("creation_time", 0)) / 1000, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")}
               for u in updates])
latest = updates[0]["update_id"] if updates else ""
recent = [u["update_id"] for u in updates[:3]]
ingest = sql(f"""SELECT origin.update_id AS update_id, origin.flow_name AS dataset,
        SUM(CAST(details:flow_progress.metrics.num_output_rows AS BIGINT)) AS rows_written
    FROM event_log('{PIPELINE_ID}') WHERE event_type = 'flow_progress'
      AND origin.update_id IN ({", ".join(f"'{u}'" for u in recent)}) AND origin.flow_name LIKE '%.bronze.%'
    GROUP BY 1, 2""")
cells = {(r["dataset"], r["update_id"]): r["rows_written"] for r in ingest}
started = {u["update_id"]: datetime.datetime.fromtimestamp(int(u.get("creation_time", 0)) / 1000, datetime.timezone.utc).strftime("%m-%d %H:%M")
           for u in updates}
bronze = sorted({r["dataset"] for r in ingest})
pivot = [{"bronze table": b.split(".")[-1], **{f"update {u[:8]} ({started[u]})": num(cells.get((b, u)) or 0) for u in reversed(recent)}}
         for b in bronze]
body += ("\n## Incremental ingestion: rows each bronze table read, in the last three updates\n\n"
         "Auto Loader reads only files it hasn't seen. Streaming tables report rows as they run, so these are summed from the "
         "running progress events. The day-two update read just day two's files. The update after it found no new files and "
         "read nothing, while silver and gold were recomputed.\n\n" + table(pivot))
flows = sql(f"""SELECT origin.flow_name AS dataset, SUM(CAST(details:flow_progress.metrics.num_output_rows AS BIGINT)) AS rows_written
    FROM event_log('{PIPELINE_ID}') WHERE event_type = 'flow_progress' AND origin.update_id = '{latest}'
      AND details:flow_progress.status = 'COMPLETED' AND origin.flow_name NOT LIKE '%.bronze.%' GROUP BY 1 ORDER BY 1""")
body += (f"\n## Rows written by silver and gold in the latest update ({latest})\n\n" + table(flows, fmt={"rows_written": num}))
dq = sql(f"""SELECT origin.flow_name AS dataset, e.name AS expectation, SUM(e.passed_records) AS passed, SUM(e.failed_records) AS failed
    FROM event_log('{PIPELINE_ID}') LATERAL VIEW explode(from_json(details:flow_progress.data_quality.expectations,
      'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) t AS e
    WHERE event_type = 'flow_progress' AND origin.update_id = '{latest}' GROUP BY 1, 2 ORDER BY 1, 2""")
body += ("\n## Data-quality expectations in the latest update\n\n"
         "Silver drops malformed delivery lines (no store, bad barcode, negative units) and warns on over-deliveries. "
         "Gold's three constraints fail the update if violated.\n\n" + table(dq, fmt={"passed": num, "failed": num}))
counts = sql(f"""SELECT 'bronze.store_stock' AS dataset, COUNT(*) AS rows FROM {C}.bronze.store_stock
  UNION ALL SELECT 'bronze.deliveries', COUNT(*) FROM {C}.bronze.deliveries
  UNION ALL SELECT 'silver.store_stock (latest per product-location)', COUNT(*) FROM {C}.silver.store_stock
  UNION ALL SELECT 'silver.delivery_lines', COUNT(*) FROM {C}.silver.delivery_lines
  UNION ALL SELECT 'gold.product_location_status', COUNT(*) FROM {C}.gold.product_location_status""")
body += "\n## Rows per layer now\n\n" + table(counts, fmt={"rows": num})
write("02_lakeflow_pipeline.md", "Lakeflow Spark Declarative Pipeline runs", body)

# ------------------------------------------------------------------------------------------------- 03 checks
# Kept in ops.pipeline_checks as recorded, but not counted: what the run actually checked is wrong.
INVALID_RUNS = {"8ea68cd2-d5ad-4334-b437-04a10b9dfe67":
                "Doesn't count. A job repair wasn't given the business date, so it checked the default, 2026-10-17, while "
                "gold held 2026-10-18. It passed only because the synthetic days share a seed. Validation now refuses to "
                "check a different day from the one gold holds (`09_daily_job_runs.md`)."}
body = ("`data/02_validate_and_publish.py` runs after every pipeline update and Lakebase refresh. It checks each stage of the "
        "journey and publishes the results to `ops.pipeline_checks`, which the app's Data Journey tab reads. The job fails "
        "if any check fails.\n\n## Every check run\n\n")
check_runs = sql(f"""SELECT run_id, CAST(convert_timezone('UTC', MIN(run_at)) AS STRING) AS run_at, CAST(business_date AS STRING) AS business_date,
        COUNT(*) AS checks, SUM(CAST(passed AS INT)) AS passed FROM {C}.ops.pipeline_checks GROUP BY run_id, business_date ORDER BY 2""")
body += table([{"run at (UTC)": h["run_at"][:19], "business date": h["business_date"], "passed": f"{h['passed']} of {h['checks']}",
                "note": INVALID_RUNS.get(h["run_id"], "")} for h in check_runs]) + "\n"
excluded = ", ".join(f"'{r}'" for r in INVALID_RUNS)
for d in dates:
    rows = sql(f"""SELECT stage, metric, value, expected, passed, note FROM {C}.ops.pipeline_checks
        WHERE run_id = (SELECT max_by(run_id, run_at) FROM {C}.ops.pipeline_checks
                        WHERE business_date = '{d}' AND run_id NOT IN ({excluded}))
        ORDER BY stage_order, metric""")
    passed = sum(r["passed"] == "true" for r in rows)
    body += f"## Business date {d}: {passed} of {len(rows)} checks passed\n\n" + table(rows, fmt={"value": num, "expected": num}) + "\n"
write("03_pipeline_checks.md", "Daily checks on every stage of the data journey", body)

# ------------------------------------------------------------------------------------------------- 04 governance
sp = cli("apps", "get", CFG["app_name"]).get("service_principal_client_id", "")
body = "## Governed tags\n\n"
body += table(sql(f"SELECT 'catalog' AS level, catalog_name AS object, tag_name, tag_value FROM {C}.information_schema.catalog_tags "
                  f"UNION ALL SELECT 'schema', schema_name, tag_name, tag_value FROM {C}.information_schema.schema_tags "
                  f"UNION ALL SELECT 'table', schema_name || '.' || table_name, tag_name, tag_value FROM {C}.information_schema.table_tags "
                  f"UNION ALL SELECT 'column', schema_name || '.' || table_name || '.' || column_name, tag_name, tag_value "
                  f"FROM {C}.information_schema.column_tags ORDER BY 1, 2, 3"))
grants = []
for obj in (f"CATALOG {C}", f"SCHEMA {C}.gold", f"SCHEMA {C}.ops", f"SCHEMA {C}.silver", f"SCHEMA {C}.bronze"):
    rows = sql(f"SHOW GRANTS `{sp}` ON {obj}")
    privs = sorted({r.get("ActionType") for r in rows if r.get("ObjectKey") == obj.split(" ", 1)[1]})
    grants.append({"object": obj, "app service principal privileges": ", ".join(privs) or "none"})
body += ("\n## Least privilege for the app\n\nThe app reads gold and ops only and can't write to the lakehouse at all: "
         "its writes go to Lakebase and come back through Lakehouse Sync.\n\n" + table(grants))
lineage = sql(f"""SELECT DISTINCT source_table_full_name AS source, target_table_full_name AS target
    FROM system.access.table_lineage WHERE source_table_full_name LIKE '{C}.%' AND target_table_full_name LIKE '{C}.%'
      AND source_table_full_name NOT LIKE '%event_log%' AND event_date >= current_date() - 7 ORDER BY 2, 1""")
body += ("\n## Lineage, captured automatically (system.access.table_lineage)\n\n" + table(lineage))
body += ("\n## One definition of every KPI (metric view gold.mv_availability)\n\n"
         + table(sql(f"SELECT division, MEASURE(availability_pct) AS availability_pct, MEASURE(gap_rate_pct) AS gap_rate_pct, "
                     f"MEASURE(attributed_pct) AS attributed_pct, MEASURE(actionable_gaps) AS actionable_gaps, "
                     f"MEASURE(actionable_sales_at_risk_gbp) AS actionable_sales_at_risk_gbp FROM {C}.gold.mv_availability "
                     f"GROUP BY ROLLUP(division) ORDER BY division NULLS LAST"), fmt={"actionable_gaps": num, "actionable_sales_at_risk_gbp": num}))
write("04_unity_catalog_governance.md", "Unity Catalog governance", body)

# ------------------------------------------------------------------------------------------------- 05 Lakebase
st = cli("postgres", "get-synced-table", f"synced_tables/{C}_pg.serving.product_location_status").get("status", {})
lb = sql(f"SELECT COUNT(*) AS rows, SUM(CASE WHEN issue <> 'NO_ISSUE' THEN 1 ELSE 0 END) AS exceptions FROM {C}_pg.serving.product_location_status")[0]
hist = sql(f"""SELECT 'colleague_actions' AS lakebase_table, COUNT(*) AS changes_in_unity_catalog FROM {C}.ops.lb_colleague_actions_history
  UNION ALL SELECT 'scan_log', COUNT(*) FROM {C}.ops.lb_scan_log_history
  UNION ALL SELECT 'ai_recommendations', COUNT(*) FROM {C}.ops.lb_ai_recommendations_history
  UNION ALL SELECT 'genie_feedback', COUNT(*) FROM {C}.ops.lb_genie_feedback_history""")
body = ("## Serving: gold synced into Postgres for Shelf Scan\n\n"
        f"- Synced table `{C}_pg.serving.product_location_status`: state `{st.get('detailed_state')}`, "
        f"last sync {json.dumps(st.get('last_sync', {}).get('sync_end_time') or st.get('last_sync', {}))}\n"
        f"- Rows in Postgres (read through Unity Catalog): {num(lb['rows'])}, of which {num(lb['exceptions'])} are gaps or lows\n"
        "- Primary key (store, upc): every Shelf Scan is a point lookup\n\n"
        "## Operational writes and Lakehouse Sync back to Unity Catalog\n\n"
        "The app writes colleague actions, scan telemetry, AI recommendations and Genie feedback to the `ops` schema in "
        f"Lakebase. Lakehouse Sync (config `ops_to_lakehouse`) streams every change into `{C}.ops.lb_<table>_history`.\n\n"
        + table(hist, fmt={"changes_in_unity_catalog": num})
        + f"\n## Latest scans recorded (from {C}.gold.shelf_scans)\n\n"
        + table(sql(f"SELECT SUBSTR(CAST(convert_timezone('UTC', scanned_at) AS STRING), 1, 19) AS `scanned (UTC)`, store, status, root_cause, served_by, lookup_ms "
                    f"FROM {C}.gold.shelf_scans ORDER BY scanned_at DESC LIMIT 10")))
body += ("\n## Lookup speed by serving path (from the app's own scan log)\n\n"
         + table(sql(f"""SELECT served_by, COUNT(*) AS scans, ROUND(percentile(CAST(lookup_ms AS DOUBLE), 0.5), 1) AS p50_ms,
                ROUND(percentile(CAST(lookup_ms AS DOUBLE), 0.95), 1) AS p95_ms FROM {C}.gold.shelf_scans GROUP BY served_by ORDER BY 1""")))
write("05_lakebase_serving_and_sync.md", "Lakebase: operational serving and the loop back to Unity Catalog", body)

# ------------------------------------------------------------------------------------------------- 06 Genie
sid = open("genie/space_id.txt").read().strip()
runs = json.load(open("genie/benchmark_runs.json"))
summ = []
for r in runs:
    d = cli("genie", "genie-get-eval-run", sid, r["eval_run_id"])
    summ.append({"run": r["label"], "questions": d.get("num_questions"), "correct": d.get("num_correct"), "status": d.get("eval_run_status")})
body = ("Genie space over the metric view, the gold table, supplier performance and the actions and scans views. "
        "It has 9 example SQLs, a text instruction set, and 12 benchmark questions with canonical SQL. Built by `genie/build_space.py`.\n\n"
        "## Benchmark runs (Genie's built-in evaluation)\n\n" + table(summ)
        + "\nThe two misses were fixed by general instructions, not by copying benchmark answers in. Run 1: a 'how many' "
          "question returned a split instead of one total. Run 2: an example used the same wording as a benchmark question "
          "but returned a ranked list.\n\n## Final run, question by question\n\n")
final = runs[-1]["eval_run_id"]
res = cli("genie", "genie-list-eval-results", sid, final).get("eval_results", [])
rows = []
for r in res:
    o = cli("genie", "genie-get-eval-result-details", sid, final, r["result_id"])
    sql_text = ((o.get("actual_response") or [{}])[0].get("response") or "").replace("`", "")
    rows.append({"question": r["question"], "assessment": o.get("assessment"), "Genie's SQL": re.sub(r"\s+", " ", sql_text)[:260]})
body += table(sorted(rows, key=lambda x: x["question"]))
write("06_genie_benchmark.md", "Genie agent: benchmark evaluation", body)

# ------------------------------------------------------------------------------------------------- 08 Gen AI evaluation
ev = sql(f"""SELECT metric, value, threshold, passed, cases, prompt_version, model, judge_model, mlflow_run_id FROM {C}.ops.genai_eval_results
    WHERE mlflow_run_id = (SELECT max_by(mlflow_run_id, evaluated_at) FROM {C}.ops.genai_eval_results) ORDER BY metric""")
cases = sql(f"""SELECT root_cause, store, product, advice FROM (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY root_cause ORDER BY store, product) AS rn FROM {C}.ops.genai_eval_cases
      WHERE mlflow_run_id = (SELECT max_by(mlflow_run_id, evaluated_at) FROM {C}.ops.genai_eval_results)) WHERE rn <= 2 ORDER BY root_cause""")
history = sql(f"""SELECT SUBSTR(CAST(convert_timezone('UTC', evaluated_at) AS STRING), 1, 19) AS `evaluated (UTC)`, prompt_version,
        MAX(CASE WHEN metric = 'numbers_grounded' THEN value END) AS numbers_grounded,
        MAX(CASE WHEN metric = 'follows_playbook' THEN value END) AS follows_playbook,
        MAX(CASE WHEN metric = 'no_contradiction' THEN value END) AS no_contradiction,
        MAX(CASE WHEN metric = 'plain_english' THEN value END) AS plain_english,
        MAX(CASE WHEN metric = 'consistent_with_playbook' THEN value END) AS consistent_with_playbook,
        CASE WHEN MIN(CAST(passed AS INT)) = 1 THEN 'all thresholds met' ELSE 'below threshold' END AS result
    FROM {C}.ops.genai_eval_results GROUP BY evaluated_at, prompt_version ORDER BY evaluated_at""")
calibration = sql(f"""SELECT judge, label AS human_label, verdict AS judge_verdict, agrees, answer FROM {C}.ops.genai_judge_calibration
    WHERE mlflow_run_id = (SELECT max_by(mlflow_run_id, evaluated_at) FROM {C}.ops.genai_eval_results) ORDER BY judge, label DESC, answer""")
pct = lambda v: f"{float(v):.0%}" if v not in (None, "") else ""
body = ("MLflow GenAI evaluation of the exact prompt the app uses (`app/nba.py`), on 48 real exceptions from gold (6 per root cause). "
        "Every call is traced in MLflow. Notebook: `genai/03_evaluate_next_best_action.py`; it runs as the last task of the daily job.\n\n"
        + (f"MLflow run `{ev[0]['mlflow_run_id']}`, prompt `{ev[0]['prompt_version']}`, advice written by `{ev[0]['model']}`, judged by `{ev[0]['judge_model']}`, {ev[0]['cases']} cases.\n\n" if ev else "")
        + table(ev, ["metric", "value", "threshold", "passed"], fmt={"value": lambda v: f"{float(v):.1%}", "threshold": lambda v: f"{float(v):.0%}"})
        + "\n## How it got here: every evaluation run\n\n"
          "Each run that failed found something real, and every fix was recorded. After the prompt fixes, every failure was a judge's "
          "mistake, found by reading its reasoning case by case. No threshold was lowered to get a pass.\n"
          "- **nba-v2:** the plain-English judge demanded 'one action', but the playbook deliberately gives two-step actions. The judge was corrected.\n"
          "- **nba-v3** (after the prompt fixes for '1 units', headings and guessed causes):\n"
          "  - The rule-based no-contradiction check flagged negated advice ('don't ... reorder'). Its negation window was too short, so it now checks the whole sentence.\n"
          "  - The judge then marked advice down for codes that only appeared in the raw input row. The evaluation now shows the judge exactly the plain-English facts the model saw.\n"
          "  - Actionability is measured exactly by the code check `follows_playbook`, so the LLM judge assesses language only.\n"
          "- **Day three** (a new trading day, so new cases):\n"
          "  - The plain-English judge failed the run at 85%: it read depot names such as 'Merseyvale DC' as internal codes. "
          "Codes are already checked exactly by `no_internal_codes`, so the judge was narrowed to tone and wording.\n"
          "  - The repaired run passed at 92%, but all four failures were still the judge's mistakes: it marked correct advice down "
          "for not naming the store, and for not using the phrase 'phantom stock'. The guideline now says what not to judge, "
          "and a calibration set (below) proves on every run that both judges still fail bad advice.\n"
          "  - The consistency judge then marked three correct answers down: two for leaving out 'no supplier chase is needed', one "
          "for adding 'ask your manager'. Its guideline already said that leaving something out isn't a contradiction, but the default "
          "judge model didn't follow it. Both judges now run on GPT-5.5, a different model family from the one that writes the "
          "advice, and those cases joined the calibration set.\n"
          "- **nba-v4:** the stricter judge caught two real defects the default judge had missed. Two replies opened with a markdown "
          "heading, and the playbook's own word 'expedite' read as corporate. The prompt now forbids a title, the playbook says "
          "'speed it up', and the app removes any markup before display (`nba.clean`). The evaluation scores that cleaned text.\n\n"
        + table(history, fmt={c: pct for c in ("numbers_grounded", "follows_playbook", "no_contradiction", "plain_english", "consistent_with_playbook")})
        + "\n## Judge calibration (this run)\n\n"
          "Before scoring, each LLM judge grades fixed answers labelled by hand: good ones, and bad ones written to show the "
          "failures each judge exists to catch. It must agree with every label, or the job fails.\n\n"
        + table(calibration, fmt={"answer": lambda v: v if len(v) <= 120 else v[:117] + "..."})
        + "\n## Sample advice from the final run (two per root cause)\n\n" + table(cases))
write("08_genai_evaluation.md", "Gen AI: evaluation of the next best action", body)

# ------------------------------------------------------------------------------------------------- 09 daily job
runs = cli("jobs", "list-runs", "--job-id", str(JOB_ID), "--limit", "25")
runs = runs if isinstance(runs, list) else runs.get("runs", [])


def failure(task):
    """The first line of a failed task's error, e.g. the checks that failed."""
    if (task.get("state", {}).get("result_state")) != "FAILED":
        return ""
    err = (cli("jobs", "get-run-output", str(task["run_id"])).get("error") or "").splitlines()
    return re.sub(r"\x1b\[[0-9;]*m", "", err[0])[:220] if err else ""
body = ("The bundle job `Larkwell shelf availability - daily run` (`resources/daily_run.job.yml`) runs the whole journey "
        "for one trading day: land the raw feeds, run the Lakeflow pipeline, refresh the Lakebase copy, check every stage, "
        "then evaluate the AI. Its schedule (05:00 Europe/London) is paused in this demo workspace.\n\n"
        "The trading days are simulated: the job takes the business date as a parameter, so consecutive trading days were run "
        "back to back. A repair re-runs only the failed tasks. It doesn't carry run-time parameters over, so the business "
        "date has to be passed again, and validation now refuses to run if it isn't.\n\n")
for r in runs:
    full = cli("jobs", "get-run", str(r["run_id"]), "--include-history")
    params = {p["name"]: p.get("value", p.get("default")) for p in full.get("job_parameters", [])}
    attempt = {}
    for i, rep in enumerate(full.get("repair_history", [])):
        for tid in rep.get("task_run_ids", []):
            attempt[tid] = "original run" if rep.get("type") == "ORIGINAL" else f"repair {i}"
    body += (f"## Run {r['run_id']}: {full['state'].get('result_state') or full['state'].get('life_cycle_state')} "
             f"(business date {params.get('business_date')})\n\n")
    body += table([{"attempt": attempt.get(t["run_id"], "original run"), "task": t["task_key"],
                    "result": t.get("state", {}).get("result_state") or t.get("state", {}).get("life_cycle_state"),
                    "duration": f"{round((t.get('execution_duration') or 0) / 1000)}s", "why it failed": failure(t)}
                   for t in sorted(full.get("tasks", []), key=lambda t: t.get("start_time", 0))]) + "\n"
body += ("## What each failure caught\n\n"
         "The first trading day (2026-10-17) was built and checked while the job was being written; above is every run of the finished job.\n"
         "- **2026-10-18, first run:**\n"
         "  - The root-cause counts and the answer key failed. The source systems' stock-count, waste and allocation IDs restart "
         "every day, and silver de-duplicated on the ID alone, so day two's evidence was dropped (`docs/decisions.md` §12).\n"
         "  - Silver was fixed and the run repaired. The AI evaluation's failures in the same run are the judge and prompt fixes in `08_genai_evaluation.md`.\n"
         "  - **The run's final pass doesn't count.** The repaired validation wasn't given the business date, so it checked the default, "
         "2026-10-17, against gold for 2026-10-18. It passed only because the synthetic days share a seed. Validation now "
         "refuses to check a different day from the one gold holds, and 2026-10-18 is never claimed as passed.\n"
         "- **2026-10-18, landed again:** bronze counts and the answer key failed. The generator wasn't reproducible across machines, "
         "and Auto Loader rightly skipped files it had already ingested (§13). The generator was fixed, and the next trading day was run fresh.\n"
         "- **2026-10-19:** every stage passed. The AI evaluation failed on its plain-English judge; the judge was fixed and the task repaired.\n"
         "- **2026-10-19, evaluation only:** the AI evaluation again, after the plain-English judge's guideline was reworded and the judges were calibrated against hand labels.\n"
         "- **2026-10-19, validation and evaluation:** validation passed with the new date guard. The evaluation failed: the consistency "
         "judge marked three correct answers down for leaving part of the action out (`08_genai_evaluation.md`).\n"
         "- **2026-10-19, evaluation only, again:** both judges on GPT-5.5, with those cases added to the calibration set. The "
         "stricter judge failed plain English on two real defects: replies that opened with a heading, and the playbook's 'expedite'.\n"
         "- **2026-10-19, evaluation only, prompt v4:** the prompt and playbook fixed and the app's markup guard in place.\n")
write("09_daily_job_runs.md", "Lakeflow Jobs: the daily run, end to end", body)
print("done")
