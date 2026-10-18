"""Run a .sql file statement by statement through the SQL Statement API, preserving whitespace exactly.

The `aitools tools query` CLI collapses indentation, which breaks the YAML inside metric view definitions.
    python3 scripts/run_sql_file.py governance/mv_availability.sql
"""
import json
import os
import re
import subprocess
import sys

CFG = json.load(open("conf/settings.json"))


def statements(text):
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--"))
    parts, buf, in_dollar = [], [], False
    for line in text.splitlines():
        if line.count("$$") % 2:
            in_dollar = not in_dollar
        buf.append(line)
        if not in_dollar and line.rstrip().endswith(";"):
            parts.append("\n".join(buf).rstrip().rstrip(";"))
            buf = []
    if "\n".join(buf).strip():
        parts.append("\n".join(buf).strip())
    return [p for p in parts if p.strip()]


ok = True
for stmt in statements(open(sys.argv[1]).read()):
    body = json.dumps({"statement": stmt, "warehouse_id": CFG["warehouse_id"], "wait_timeout": "50s"})
    out = subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--json", body, "--profile", os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT")],
                         capture_output=True, text=True).stdout
    st = json.loads(out or "{}").get("status", {})
    ok &= st.get("state") == "SUCCEEDED"
    print(f"{st.get('state', 'ERROR'):<10} {re.sub(r'\\s+', ' ', stmt)[:110]}  {st.get('error', {}).get('message', '')[:200]}")
sys.exit(0 if ok else 1)
