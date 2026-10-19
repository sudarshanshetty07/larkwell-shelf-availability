"""End-to-end test of the deployed Larkwell Shelf Availability app.

Exercises every stage a user touches: dashboards and drill-downs (SQL warehouse), Shelf Scan (Lakebase), the next best
action (LLM), colleague actions flowing Lakebase -> Lakehouse Sync -> Unity Catalog, tomorrow's watch list from the
gap-risk model, curated analyses, Genie answers with result tables, feedback, and the Data Journey checks. Ends with a
latency comparison of Lakebase and the warehouse.

Writes one test action and one feedback row (both clearly marked as tests).

    uv run --with requests python scripts/e2e_test.py | tee evidence/07_app_e2e_test.txt
"""
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.parse

import requests

PROFILE = os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
CFG = json.load(open("conf/settings.json"))
CATALOG = CFG["catalog"]
APP_NAME = CFG["app_name"]
PROMPT_VERSION = re.search(r'PROMPT_VERSION = "([^"]+)"', open("app/nba.py").read()).group(1)
STORE = "Covent Garden"
CODES = re.compile(r"\b(KNOWN_GAP|SUPPLIER_SHORT|ORDER_DELIVERY_BLOCK|STOCKFILE_ADJUSTMENT|UNDER_FORECAST|INVESTIGATE)\b")


def cli_json(*args):
    out = subprocess.run(["databricks", *args, "--profile", PROFILE, "-o", "json"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


APP = cli_json("apps", "get", APP_NAME)["url"]
tok = json.loads(subprocess.run(["databricks", "auth", "token", "--profile", PROFILE], capture_output=True, text=True,
                                check=True).stdout)["access_token"]
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {tok}"})
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:260])


def get(path, **params):
    t0 = time.perf_counter()
    r = S.get(APP + path, params=params, timeout=120)
    return r, time.perf_counter() - t0


def sql(statement):
    body = json.dumps({"statement": statement, "warehouse_id": CFG["warehouse_id"], "wait_timeout": "50s"})
    d = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--json", body,
                                   "--profile", PROFILE], capture_output=True, text=True).stdout)
    cols = [c["name"] for c in d["manifest"]["schema"]["columns"]]
    return [dict(zip(cols, row)) for row in d.get("result", {}).get("data_array", [])]


print(f"App under test: {APP_NAME}\n")

# ---------------------------------------------------------------- page and assets
r, _ = get("/")
html = r.text
check("page loads", r.status_code == 200, f"{len(html)} bytes")
check("page title", "<title>Larkwell Shelf Availability</title>" in html)
check("navigation includes Shelf Scan and Data Journey", "Shelf Scan" in html and "Data Journey" in html)
js, _ = get("/static/app.js?v=11")
check("no scripted 'thinking' messages in the frontend", "_loadSteps" not in js.text and "Composing your answer" not in js.text)

# ---------------------------------------------------------------- reference endpoints
check("/api/me returns an admin", get("/api/me")[0].json().get("is_admin") is True)
h = get("/api/health")[0].json()
check("/api/health: Lakebase connected", h["lakebase"].get("ok") is True, json.dumps(h["lakebase"]))
fj = get("/api/filters")[0].json()
check("/api/filters: 5 formats and 13 categories",
      fj.get("stgs") == ["Forecourt", "Local", "Outlet", "Superstore", "Travel"] and len(fj.get("categories", [])) == 13)
stores = get("/api/stores")[0].json().get("stores", [])
check("/api/stores: 900 stores", len(stores) == 900 and STORE in stores, str(len(stores)))
check("/api/divisions", set(get("/api/divisions")[0].json().get("divisions", {})) == {"Central", "North & Scotland", "South"})

# ---------------------------------------------------------------- dashboards (SQL warehouse over gold)
PERSONAS = ["support_centre_store", "support_centre_category", "retail_regional", "retail_store_manager"]
dash_t = []
for persona in PERSONAS:
    for scope in ("owned", "franchise", "all"):
        d, t = get("/api/dashboard", persona=persona, issue_filter="all", scope_filter=scope)
        dash_t.append(t)
        tot = d.json().get("totals", {}) if d.status_code == 200 else {}
        ok = d.status_code == 200 and d.json().get("table")
        if scope == "all":
            ok = ok and int(tot.get("gaps", 0)) == 133765 and int(tot.get("lows", 0)) == 72069 and int(tot.get("total_pls", 0)) == 5400000
        if scope == "owned":
            ok = ok and int(tot.get("total_pls", 0)) == 4908000
        check(f"dashboard {persona} scope={scope}", ok, f"gaps={tot.get('gaps')} lows={tot.get('lows')} pls={tot.get('total_pls')} {t:.1f}s")

paths = [
    ("support_centre_store", [dict(drill_dimension="division"), dict(drill_dimension="area", division="South"),
                              dict(drill_dimension="stg", division="South", area="London"),
                              dict(drill_dimension="store", division="South", area="London", stg="Superstore"),
                              dict(drill_dimension="product", store=STORE)]),
    ("support_centre_category", [dict(drill_dimension="cluster"), dict(drill_dimension="category", cluster="Chilled"),
                                 dict(drill_dimension="superGroup", category="Ready Meals"),
                                 dict(drill_dimension="productGroup", category="Ready Meals", super_group="Chilled"),
                                 dict(drill_dimension="product", category="Ready Meals", product_group="Pub Classics")]),
    ("retail_regional", [dict(drill_dimension="area", division="South"), dict(drill_dimension="store", division="South", area="London"),
                         dict(drill_dimension="product", store=STORE)]),
    ("retail_store_manager", [dict(drill_dimension="category", store=STORE), dict(drill_dimension="product", store=STORE, category="Bakery")]),
]
for persona, steps in paths:
    for p in steps:
        d, t = get("/api/drill", persona=persona, issue_filter="all", scope_filter="all", **p)
        items = d.json().get("items", []) if d.status_code == 200 else []
        check(f"drill {persona} -> {p['drill_dimension']}", d.status_code == 200 and items, f"{len(items)} items {t:.1f}s")
b = get(f"/api/store-briefing/{urllib.parse.quote(STORE)}", persona="support_centre_store")[0].json()
check("morning briefing", b.get("reasons") and b.get("category_reason_breakdown"), f"gaps={b.get('kpis', {}).get('gaps')}")

# ---------------------------------------------------------------- Shelf Scan (Lakebase)
sm = get("/api/sst-samples", store=STORE)[0].json()
samples = sm.get("samples", [])
check("Shelf Scan samples served from Lakebase, one per root cause", sm.get("served_by") == "lakebase" and len(samples) == 8,
      f"{len(samples)} reasons")
events = {}
for s in samples:
    j = get("/api/sst-lookup", store=STORE, upc=s["upc"])[0].json()
    events[s["consensus_reason"]] = j
    check(f"scan {s['consensus_reason']} from Lakebase",
          j.get("status") == "ISSUE_FOUND" and j["sst_display"]["reason_code"] == s["consensus_reason"] and j.get("served_by") == "lakebase",
          f"{j['sst_display']['product']} in {j.get('lookup_ms')} ms, actions={[a['type'] for a in j['sst_display'].get('actions', [])]}")
healthy = sql(f"SELECT upc FROM {CATALOG}.gold.product_location_status WHERE store = '{STORE}' AND issue = 'NO_ISSUE' LIMIT 1")[0]["upc"]
j = get("/api/sst-lookup", store=STORE, upc=healthy)[0].json()
check("scan a healthy line", j.get("status") == "NO_ISSUE" and j["sst_display"]["status"] == "AVAILABLE")
check("scan an unknown barcode", get("/api/sst-lookup", store=STORE, upc="0000000000000")[0].json().get("status") == "NOT_FOUND")
lb = events["SUPPLIER_SHORT"]
wh = get("/api/sst-lookup", store=STORE, upc=lb["upc"], source="warehouse")[0].json()
check("warehouse fallback gives the same answer as Lakebase",
      wh.get("served_by") == "warehouse" and wh["sst_display"] == lb["sst_display"], f"warehouse {wh.get('lookup_ms')} ms vs Lakebase {lb.get('lookup_ms')} ms")

# ---------------------------------------------------------------- next best action (LLM, playbook-driven)
for reason in ("SUPPLIER_SHORT", "KNOWN_GAP", "STOCKFILE_ADJUSTMENT"):
    ev = events[reason]
    t0 = time.perf_counter()
    x = S.post(APP + "/api/sst-explain", json={"store": STORE, "upc": ev["upc"], "event_data": ev["event"]}, timeout=90).json()
    txt = x.get("explanation", "")
    check(f"next best action {reason}", len(txt) > 40 and not CODES.search(txt) and x.get("prompt_version") == PROMPT_VERSION
          and x.get("model") != "fallback-template", f"{time.perf_counter() - t0:.1f}s :: {txt[:140]}")

# ---------------------------------------------------------------- colleague actions: app -> Lakebase -> Unity Catalog
ev = events["SUPPLIER_SHORT"]
bad = S.post(APP + "/api/actions", json={"store": STORE, "upc": ev["upc"], "action_type": "DELETE_EVERYTHING"}, timeout=30)
check("unknown action type rejected (400)", bad.status_code == 400)
t_logged = time.time()
a = S.post(APP + "/api/actions", json={"store": STORE, "upc": ev["upc"], "action_type": "RAISED_SHORTAGE_QUERY",
                                       "note": "e2e test action"}, timeout=30).json()
action_id = (a.get("action") or {}).get("action_id")
check("action saved to Lakebase", a.get("status") == "ok" and action_id, f"action_id={action_id}")
listed = get("/api/actions", store=STORE)[0].json().get("actions", [])
check("action listed for the store straight away", any(str(x["action_id"]) == str(action_id) for x in listed))
seen_after = None
for _ in range(40):
    rows = sql(f"SELECT action_id, root_cause, action_type FROM {CATALOG}.gold.colleague_actions WHERE action_id = {action_id}")
    if rows:
        seen_after = time.time() - t_logged
        break
    time.sleep(10)
check("action reached Unity Catalog via Lakehouse Sync", seen_after is not None and rows[0]["root_cause"] == "SUPPLIER_SHORT",
      f"visible in gold.colleague_actions after {seen_after:.0f}s" if seen_after else "not seen within 400s")

# ---------------------------------------------------------------- tomorrow's watch list: the gap-risk model (ML)
w, t = get("/api/gap-risk", store=STORE)
wj = w.json() if w.status_code == 200 else {}
listed = wj.get("new_risk", []) + wj.get("fix_first", [])
risks = [float(r["risk"]) for r in wj.get("new_risk", [])]
check("watch list: 10 lines that look fine and 5 to fix first, each with a reason",
      wj.get("available") and len(wj.get("new_risk", [])) == 10 and len(wj.get("fix_first", [])) == 5
      and all(r.get("reason_1") for r in listed), f"model v{wj.get('model', {}).get('model_version')}, {t:.1f}s")
check("watch list is ranked by a probability", risks == sorted(risks, reverse=True) and all(0 < x < 1 for x in risks),
      f"top risk {risks[0]:.0%}" if risks else "")
top = sql(f"SELECT product FROM {CATALOG}.ml.gap_risk_scores WHERE store = '{STORE}' AND looks_fine AND "
          f"business_date = (SELECT MAX(business_date) FROM {CATALOG}.ml.gap_risk_scores) ORDER BY risk DESC LIMIT 1")
check("watch list matches the predictions table in Unity Catalog", top and wj["new_risk"][0]["product"] == top[0]["product"],
      top[0]["product"] if top else "")
met = {k: float(v) for k, v in wj.get("model", {}).get("metrics", {}).get("all.list_precision", {}).items() if v not in (None, "")}
check("champion beat the today rule on its unseen test week", met and met["model"] > met["today_rule"],
      f"{met.get('model', 0):.0%} vs {met.get('today_rule', 0):.0%} of watch-list lines empty next morning")
grades = wj.get("model", {}).get("recent_grades", [])
check("the model is graded every morning", len(grades) >= 7 and wj.get("store_grade"),
      f"last {len(grades)} mornings; {STORE} yesterday's list: {wj.get('store_grade', {}).get('listed_empty')} of "
      f"{wj.get('store_grade', {}).get('listed')} empty")

# ---------------------------------------------------------------- chat: curated analyses and Genie
qs = get("/api/suggested-questions")[0].json().get("questions", [])
check("four curated questions offered", len(qs) == 4)
for q in qs:
    t0 = time.perf_counter()
    c = S.post(APP + "/api/chat", json={"message": q, "store_name": STORE}, timeout=120).json()
    el = time.perf_counter() - t0
    check(f"curated analysis: {q[:40]}...", c.get("source") == "curated" and "|---|" in c.get("text", "") and el < 6,
          f"{el:.1f}s, no artificial delay")
t0 = time.perf_counter()
g = S.post(APP + "/api/chat", json={"message": "Which depot has the most order or delivery blocks?"}, timeout=180).json()
check("Genie answers with a result table and its SQL", g.get("source") == "genie" and g.get("rows") and g.get("columns") and g.get("sql"),
      f"{time.perf_counter() - t0:.0f}s :: {g.get('rows', [])[:1]}")
fb = S.post(APP + "/api/feedback", json={"conversation_id": g["conversation_id"], "message_id": g["message_id"], "is_positive": True,
                                         "comment": "e2e test", "question": "depot blocks", "answer": g.get("text", "")[:200],
                                         "sql": g.get("sql", "")}, timeout=60)
check("feedback accepted", fb.status_code == 200 and fb.json().get("status") == "ok")

# ---------------------------------------------------------------- Data Journey
jj = get("/api/journey")[0].json()
checks = jj.get("checks", [])
check("Data Journey: the daily run's checks are published and all passed",
      len(checks) >= 43 and all(c["passed"] in (True, "true") for c in checks), f"{len(checks)} checks")
check("Data Journey: tomorrow's predictions cover every ranged line", int(jj.get("ml", {}).get("scored") or 0) > 5_000_000,
      json.dumps(jj.get("ml")))
check("Data Journey: Lakebase holds every product-location", int(jj.get("lakebase", {}).get("serving_rows", 0)) == 5400000,
      json.dumps(jj.get("lakebase")))

# ---------------------------------------------------------------- latency: Lakebase vs warehouse (server-side lookup time)
sample = sql(f"SELECT store, upc FROM {CATALOG}.gold.product_location_status TABLESAMPLE (0.01 PERCENT) REPEATABLE (7) LIMIT 60")
lb_ms, lb_rt, wh_ms = [], [], []
for i, row in enumerate(sample):
    r, t = get("/api/sst-lookup", store=row["store"], upc=row["upc"])
    lb_ms.append(float(r.json()["lookup_ms"]))
    lb_rt.append(t * 1000)
    if i < 20:
        w = get("/api/sst-lookup", store=row["store"], upc=row["upc"], source="warehouse")[0].json()
        wh_ms.append(float(w["lookup_ms"]))


def p(xs, q):
    xs = sorted(xs)
    return xs[int(round(q * (len(xs) - 1)))]


print(f"\nShelf Scan lookup, measured inside the app: Lakebase p50 {statistics.median(lb_ms):.1f} ms, p95 {p(lb_ms, .95):.1f} ms (n={len(lb_ms)}) | "
      f"SQL warehouse p50 {statistics.median(wh_ms):.0f} ms, p95 {p(wh_ms, .95):.0f} ms (n={len(wh_ms)})")
print(f"Shelf Scan round trip from this laptop (includes internet latency): p50 {statistics.median(lb_rt):.0f} ms, p95 {p(lb_rt, .95):.0f} ms")
print(f"Dashboard response: p50 {statistics.median(dash_t):.2f}s, max {max(dash_t):.2f}s (n={len(dash_t)})")
check("Lakebase lookups are at least 50x faster than the warehouse", statistics.median(wh_ms) / statistics.median(lb_ms) >= 50,
      f"{statistics.median(wh_ms) / statistics.median(lb_ms):.0f}x")

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
sys.exit(1 if fails else 0)
