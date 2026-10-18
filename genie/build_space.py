"""Build, validate and create the Genie space for Larkwell Shelf Availability.

python3 genie/build_space.py --validate          run every example and benchmark SQL against the warehouse
python3 genie/build_space.py --emit > space.json write the serialized_space
python3 genie/build_space.py --create            create the space and save its id to genie/space_id.txt
python3 genie/build_space.py --update            push the current definition to the existing space
"""
import json
import os
import subprocess
import sys

PROFILE = os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "conf", "settings.json")))
C = CFG["catalog"]
PLS, MV = f"{C}.gold.product_location_status", f"{C}.gold.mv_availability"
ACTIONS, SCANS, SUPPLIER = f"{C}.gold.colleague_actions", f"{C}.gold.shelf_scans", f"{C}.gold.dim_supplier"
TITLE = "Larkwell Shelf Availability"
DESCRIPTION = ("On-shelf availability and root causes for Larkwell Foods, a fictitious UK food retailer (synthetic data): "
               "governed KPIs, every product-location's status and root cause, supplier performance, and the actions "
               "store colleagues have logged.")


def hid(n):
    return f"{n:032x}"


SAMPLE_QUESTIONS = [
    "What is on-shelf availability by division?",
    "Which suppliers are causing the most supplier shorts?",
    "Which depot has the most order or delivery blocks?",
    "Show the root-cause mix for Covent Garden",
    "What actions have stores logged today, and for which root causes?",
    "Which suppliers have the lowest fill rate?",
]

EXAMPLES = [  # (question, sql, usage guidance)
    ("What is on-shelf availability by division?",
     f"SELECT division, MEASURE(availability_pct) AS availability_pct, MEASURE(gap_rate_pct) AS gap_rate_pct "
     f"FROM {MV} GROUP BY division ORDER BY availability_pct",
     "Use the metric view for any KPI: availability, gap rate, attributed %, actionable gaps or sales at risk."),
    ("What is the gap rate by store format?",
     f"SELECT store_format, MEASURE(gap_rate_pct) AS gap_rate_pct, MEASURE(gaps) AS gaps "
     f"FROM {MV} GROUP BY store_format ORDER BY gap_rate_pct DESC",
     "Gap rate is gaps over all product-locations in scope; always take it from the metric view."),
    ("Which suppliers cause the most supplier shorts?",
     f"SELECT product_location_status.supplier, COUNT(*) AS supplier_shorts, "
     f"SUM(product_location_status.supplier_short_qty) AS units_short FROM {PLS} "
     f"WHERE product_location_status.consensus_reason = 'SUPPLIER_SHORT' "
     f"GROUP BY product_location_status.supplier ORDER BY supplier_shorts DESC LIMIT 10",
     "Use for ranking suppliers, depots or products by a single root cause."),
    ("What is the root-cause mix for Covent Garden?",
     f"SELECT product_location_status.consensus_reason, COUNT(*) AS exceptions, "
     f"ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct FROM {PLS} "
     f"WHERE product_location_status.store = 'Covent Garden' AND product_location_status.issue <> 'NO_ISSUE' "
     f"GROUP BY product_location_status.consensus_reason ORDER BY exceptions DESC",
     "Use for the share of gaps and lows by root cause for one store or any scope."),
    ("Rank the depots by order or delivery blocks",
     f"SELECT product_location_status.depot, COUNT(*) AS delivery_blocks, "
     f"COUNT(DISTINCT product_location_status.store) AS stores_affected FROM {PLS} "
     f"WHERE product_location_status.consensus_reason = 'ORDER_DELIVERY_BLOCK' "
     f"GROUP BY product_location_status.depot ORDER BY delivery_blocks DESC",
     "Use for depot and logistics questions."),
    ("Which stores have the highest gap rate compared with stores of the same format?",
     f"WITH s AS (SELECT product_location_status.store, product_location_status.site_trading_group, "
     f"100.0 * SUM(CASE WHEN product_location_status.issue = 'GAP' THEN 1 ELSE 0 END) / COUNT(*) AS gap_rate_pct "
     f"FROM {PLS} GROUP BY product_location_status.store, product_location_status.site_trading_group), "
     f"r AS (SELECT s.store, s.site_trading_group, s.gap_rate_pct, "
     f"AVG(s.gap_rate_pct) OVER (PARTITION BY s.site_trading_group) AS format_avg_pct FROM s) "
     f"SELECT r.store, r.site_trading_group AS store_format, ROUND(r.gap_rate_pct, 1) AS gap_rate_pct, "
     f"ROUND(r.format_avg_pct, 1) AS format_avg_pct, ROUND(r.gap_rate_pct - r.format_avg_pct, 1) AS gap_vs_format_pts "
     f"FROM r ORDER BY gap_vs_format_pts DESC LIMIT 10",
     "Use for peer comparisons: compare each store with the average of stores of the same format."),
    ("What actions have stores logged today, and for which root causes?",
     f"SELECT colleague_actions.action_type, colleague_actions.root_cause, COUNT(*) AS actions, "
     f"COUNT(DISTINCT colleague_actions.store) AS stores FROM {ACTIONS} "
     f"WHERE colleague_actions.created_at >= current_date() "
     f"GROUP BY colleague_actions.action_type, colleague_actions.root_cause ORDER BY actions DESC",
     "Use colleague_actions for anything about what stores did. It updates within about a minute of an action."),
    ("Which suppliers have the lowest fill rate?",
     f"SELECT dim_supplier.supplier, dim_supplier.category_specialism, dim_supplier.fill_rate_pct, "
     f"dim_supplier.contracted_service_level_pct, dim_supplier.units_short FROM {SUPPLIER} "
     f"ORDER BY dim_supplier.fill_rate_pct ASC LIMIT 10",
     "Use dim_supplier for supplier delivery performance against the contracted service level."),
    ("What is the estimated sales at risk by root cause?",
     f"SELECT root_cause, MEASURE(exceptions) AS exceptions, MEASURE(sales_at_risk_gbp) AS sales_at_risk_gbp "
     f"FROM {MV} WHERE root_cause IS NOT NULL GROUP BY root_cause ORDER BY sales_at_risk_gbp DESC",
     "Sales at risk is an estimate: forecast demand not covered by stock on hand, at selling price. Say so."),
]

BENCHMARKS = [  # deterministic questions with one canonical answer
    ("What is the overall on-shelf availability?", f"SELECT MEASURE(availability_pct) AS availability_pct FROM {MV}"),
    ("What is the gap rate by store format?",
     f"SELECT store_format, MEASURE(gap_rate_pct) AS gap_rate_pct FROM {MV} GROUP BY store_format ORDER BY gap_rate_pct DESC"),
    ("How many gaps and lows are there in the South division?",
     f"SELECT MEASURE(gaps) AS gaps, MEASURE(lows) AS lows FROM {MV} WHERE division = 'South'"),
    ("Which 5 suppliers have the most supplier shorts?",
     f"SELECT supplier, COUNT(*) AS supplier_shorts FROM {PLS} WHERE consensus_reason = 'SUPPLIER_SHORT' "
     f"GROUP BY supplier ORDER BY supplier_shorts DESC LIMIT 5"),
    ("Which depot has the most order or delivery blocks?",
     f"SELECT depot, COUNT(*) AS delivery_blocks FROM {PLS} WHERE consensus_reason = 'ORDER_DELIVERY_BLOCK' "
     f"GROUP BY depot ORDER BY delivery_blocks DESC LIMIT 1"),
    ("What share of gaps and lows have a confirmed root cause?",
     f"SELECT MEASURE(attributed_pct) AS attributed_pct FROM {MV}"),
    ("How many actionable gaps are there in Bakery?",
     f"SELECT MEASURE(actionable_gaps) AS actionable_gaps FROM {MV} WHERE category = 'Bakery'"),
    ("What is the root-cause mix at Covent Garden?",
     f"SELECT consensus_reason, COUNT(*) AS exceptions FROM {PLS} WHERE store = 'Covent Garden' AND issue <> 'NO_ISSUE' "
     f"GROUP BY consensus_reason ORDER BY exceptions DESC"),
    ("Which 5 suppliers have the lowest fill rate?",
     f"SELECT supplier, fill_rate_pct FROM {SUPPLIER} ORDER BY fill_rate_pct ASC LIMIT 5"),
    ("What is the estimated sales at risk from supplier shorts?",
     f"SELECT MEASURE(sales_at_risk_gbp) AS sales_at_risk_gbp FROM {MV} WHERE root_cause = 'SUPPLIER_SHORT'"),
    ("How many space lows are there in each category?",
     f"SELECT category, MEASURE(lows) AS space_lows FROM {MV} WHERE low_type = 'SPACE_LOW' GROUP BY category ORDER BY space_lows DESC"),
    ("How many gaps and lows had more than one kind of evidence?",
     f"SELECT COUNT(*) AS exceptions FROM {PLS} WHERE issue <> 'NO_ISSUE' AND evidence_found LIKE '%,%'"),
]

PLS_COLUMNS = {  # column -> (synonyms, entity matching)
    "store": (["store name", "shop", "branch"], True),
    "division": (["region"], True),
    "area": (["store area"], True),
    "site_trading_group": (["store format", "format", "store type"], True),
    "business_scope": (["owned or franchise", "ownership", "franchise"], True),
    "cluster": (["temperature zone", "temp zone"], True),
    "super_group": (["department"], True),
    "category": (["product category"], True),
    "product_group": (["sub-category", "range"], True),
    "product": (["line", "item", "SKU"], False),
    "supplier": (["vendor"], True),
    "depot": (["distribution centre", "DC", "warehouse"], True),
    "issue": (["status", "shelf status", "availability status"], True),
    "low_issue": (["low type"], True),
    "consensus_reason": (["reason", "reason code", "root cause", "cause"], True),
    "consensus_reason_retail": (["store reason", "retail reason code"], True),
    "supplier_short_type": (["short type", "type of short"], True),
    "days_of_cover": (["cover", "days cover"], False),
    "est_sales_at_risk_gbp": (["sales at risk", "lost sales estimate"], False),
    "evidence_found": (["evidence", "signals"], False),
}
PLS_EXCLUDE = ["elimination", "msc_decrease"]           # reserved columns, always false

TEXT = f"""## PURPOSE
- Answer on-shelf availability and root-cause questions for Larkwell Foods, a fictitious UK food retailer. All data is synthetic.
- Users are head-office availability analysts, category managers, and regional and store managers.

## WHERE TO LOOK
- KPIs (availability, gap rate, attributed %, actionable gaps, sales at risk): mv_availability with MEASURE(). It holds the governed definitions.
- Individual product-locations, evidence quantities, suppliers and depots: product_location_status, one row per store x line for the business day.
- What stores did about gaps: colleague_actions. Shelf Scan usage and speed: shelf_scans.
- Supplier delivery performance (fill rate, units short): dim_supplier.

## DISAMBIGUATION
- A "PL" or "product-location" is one store x line. "Gaps" means issue = GAP, "lows" means issue = LOW, and "exceptions" means GAP or LOW.
- "Availability" or "OSA" means availability_pct, and "gap rate" means gap_rate_pct, both from mv_availability.
- "Reason", "root cause" or "reason code" means consensus_reason (root_cause in mv_availability and colleague_actions).
- "Format" or "store type" means site_trading_group (store_format in the metric view). "Department" means super_group.
- "Actionable gaps" exclude KNOWN_GAP, which are deliberate range exits.
- "Today" means the latest business_date in product_location_status; for colleague_actions use created_at.

## DATA QUALITY NOTES
- product_location_status is one daily snapshot, so never imply trends across days.
- consensus_reason and low_issue are NULL when issue = NO_ISSUE.
- Columns ending in _qty are units for the chosen root cause and 0 otherwise; evidence_found lists every kind of evidence present.
- "More than one kind of evidence" means evidence_found contains a comma.
- Sales at risk is an estimate (forecast demand not covered by stock on hand, at selling price). Say so when you use it.

## CONSTRAINTS
- If the data can't answer a question (customer behaviour, margin, competitor prices, trends over time), say so plainly instead of estimating.

## Instructions you must follow when providing summaries
- When asked "how many" without a request for a breakdown, return a single total, not a split by status or any other dimension.
- Round percentages to one decimal place and label estimates as estimates.
- State the scope you used: a store, area, division or the whole estate."""


def build():
    pls_cols = []
    for name, (syn, em) in PLS_COLUMNS.items():
        c = {"column_name": name, "synonyms": syn, "enable_format_assistance": True}
        if em:
            c["enable_entity_matching"] = True
        pls_cols.append(c)
    pls_cols += [{"column_name": n, "exclude": True} for n in PLS_EXCLUDE]
    tables = [
        {"identifier": ACTIONS, "column_configs": sorted([
            {"column_name": "action_type", "synonyms": ["action", "what they did"], "enable_format_assistance": True, "enable_entity_matching": True},
            {"column_name": "root_cause", "synonyms": ["reason", "cause"], "enable_format_assistance": True, "enable_entity_matching": True},
            {"column_name": "store", "enable_format_assistance": True, "enable_entity_matching": True}], key=lambda c: c["column_name"])},
        {"identifier": SUPPLIER, "column_configs": sorted([
            {"column_name": "supplier", "synonyms": ["vendor"], "enable_format_assistance": True, "enable_entity_matching": True},
            {"column_name": "fill_rate_pct", "synonyms": ["fill rate", "service level achieved"], "enable_format_assistance": True}],
            key=lambda c: c["column_name"])},
        {"identifier": PLS, "column_configs": sorted(pls_cols, key=lambda c: c["column_name"])},
        {"identifier": SCANS},
    ]
    space = {
        "version": 2,
        "config": {"sample_questions": [{"id": hid(0x1000 + i), "question": [q]} for i, q in enumerate(SAMPLE_QUESTIONS)]},
        "data_sources": {"tables": sorted(tables, key=lambda t: t["identifier"]), "metric_views": [{"identifier": MV}]},
        "instructions": {
            "text_instructions": [{"id": hid(0x3000), "content": [TEXT]}],
            "example_question_sqls": [{"id": hid(0x2000 + i), "question": [q], "sql": [s], "usage_guidance": [g]}
                                      for i, (q, s, g) in enumerate(EXAMPLES)],
        },
        "benchmarks": {"questions": [{"id": hid(0x4000 + i), "question": [q], "answer": [{"format": "SQL", "content": [s]}]}
                                     for i, (q, s) in enumerate(BENCHMARKS)]},
    }
    assert len(TEXT) < 5000, len(TEXT)
    return space


def run_sql(sql):
    body = json.dumps({"statement": sql, "warehouse_id": CFG["warehouse_id"], "wait_timeout": "50s"})
    r = subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--json", body, "--profile", PROFILE],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    st = d.get("status", {})
    if st.get("state") != "SUCCEEDED":
        return None, st.get("error", {}).get("message", r.stderr[-300:])
    return d.get("result", {}).get("data_array", []), None


def space_body():
    return {"warehouse_id": CFG["warehouse_id"], "title": TITLE, "description": DESCRIPTION,
            "parent_path": f"/Workspace/Users/{me()}/{CFG['workspace_folder']}", "serialized_space": json.dumps(build())}


def me():
    r = subprocess.run(["databricks", "current-user", "me", "--profile", PROFILE, "-o", "json"], capture_output=True, text=True)
    return json.loads(r.stdout)["userName"]


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    if "--validate" in sys.argv:
        bad = 0
        for kind, items in (("example", [(q, s) for q, s, _ in EXAMPLES]), ("benchmark", BENCHMARKS)):
            for q, s in items:
                rows, err = run_sql(s)
                bad += rows is None
                print(f"{'OK ' if rows is not None else 'ERR'} {kind:9s} {q[:70]:<70} -> {len(rows) if rows is not None else err[:200]} rows"
                      + (f" | first: {rows[0]}" if rows else ""))
        sys.exit(1 if bad else 0)
    if "--emit" in sys.argv:
        print(json.dumps(build(), indent=2))
    if "--create" in sys.argv or "--update" in sys.argv:
        body = space_body()
        if "--update" in sys.argv:
            sid = open(os.path.join(here, "space_id.txt")).read().strip()
            cmd = ["databricks", "genie", "update-space", sid, "--json", json.dumps(body), "--profile", PROFILE, "-o", "json"]
        else:
            cmd = ["databricks", "genie", "create-space", "--json", json.dumps(body), "--profile", PROFILE, "-o", "json"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            sys.exit(r.stderr[-2000:])
        d = json.loads(r.stdout)
        open(os.path.join(here, "space_id.txt"), "w").write(d["space_id"])
        print("space", d["space_id"], d.get("title"))
