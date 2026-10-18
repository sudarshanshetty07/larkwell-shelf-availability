"""
Larkwell Shelf Availability: FastAPI backend.

Larkwell Foods is a fictitious UK food retailer; all data is synthetic.

Where the data comes from:
- Dashboards, drill-downs and the morning briefing query the gold table the Lakeflow pipeline builds
  (larkwell_osa.gold.product_location_status) on a SQL warehouse.
- Shelf Scan reads the same table from Lakebase, where Unity Catalog keeps a synced copy for millisecond lookups.
- Colleague actions, scan telemetry, AI recommendations and Genie feedback are written to Lakebase, and Lakehouse
  Sync streams them back to Unity Catalog.
- Ask the data uses a Genie space. The next best action uses a Databricks-hosted LLM (see nba.py).
"""
import os
import re
import json
import time
import base64
import logging
from typing import Optional

import threading
import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

import lakebase
import nba

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Larkwell Shelf Availability")

# --- Config (resource IDs come from app.yaml) ---
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "")
CATALOG = os.getenv("UC_CATALOG", "larkwell_osa")
TABLE = f"{CATALOG}.gold.product_location_status"

# --- Auth ---
_token_cache: dict = {"token": "", "expires_at": 0}


def _get_host() -> str:
    host = os.environ.get("DATABRICKS_HOST", "")
    if not host.startswith("http"):
        host = "https://" + host
    return host.rstrip("/")


def get_token() -> str:
    injected = os.getenv("DATABRICKS_TOKEN", "")
    if injected:
        return injected
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]
    host = _get_host()
    client_id = os.getenv("DATABRICKS_CLIENT_ID", "")
    client_secret = os.getenv("DATABRICKS_CLIENT_SECRET", "")
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = requests.post(
        f"{host}/oidc/v1/token",
        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
        data="grant_type=client_credentials&scope=all-apis",
        timeout=15,
    )
    r.raise_for_status()
    d = r.json()
    _token_cache["token"] = d["access_token"]
    _token_cache["expires_at"] = now + d.get("expires_in", 3600)
    return _token_cache["token"]


def _headers():
    return {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}


def _clean(v):
    if not isinstance(v, str):
        return v
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', v)


def _safe_str(val: str | None) -> str:
    if not val:
        return ""
    return val.replace("'", "''")


# --- SQL Execution ---
def execute_sql(sql: str) -> list[dict]:
    host = _get_host()
    r = requests.post(
        f"{host}/api/2.0/sql/statements",
        json={"statement": sql, "warehouse_id": WAREHOUSE_ID, "wait_timeout": "50s", "on_wait_timeout": "CANCEL"},
        headers=_headers(),
        timeout=60,
    )
    data = r.json()
    state = data.get("status", {}).get("state", "")
    if state != "SUCCEEDED":
        err = data.get("status", {}).get("error", {}).get("message", str(data))
        logger.error(f"SQL failed ({state}): {err}\nSQL: {sql[:200]}")
        raise HTTPException(status_code=500, detail=f"SQL failed ({state}): {err}")
    cols = [c["name"] for c in data["manifest"]["schema"]["columns"]]
    rows = data.get("result", {}).get("data_array", [])
    return [{cols[i]: _clean(row[i]) for i in range(len(cols))} for row in rows]


# --- RBAC: Role-Based Access Control ---
ROLES_TABLE = f"{CATALOG}.ops.app_user_roles"
_role_cache: dict = {}  # email → {persona, store_filter, division_filter, is_admin}
_role_cache_ts: float = 0
ROLE_CACHE_TTL = 300  # 5 minutes


def _load_roles():
    """Load all user roles from UC table into memory cache."""
    global _role_cache, _role_cache_ts
    try:
        rows = execute_sql(f"SELECT email, persona, store_filter, division_filter, is_admin FROM {ROLES_TABLE}")
        cache = {}
        for r in rows:
            cache[r["email"].lower().strip()] = {
                "persona": r["persona"],
                "store_filter": r["store_filter"],
                "division_filter": r["division_filter"],
                "is_admin": r["is_admin"] == "true" or r["is_admin"] is True,
            }
        _role_cache = cache
        _role_cache_ts = time.time()
        logger.info(f"RBAC: loaded {len(cache)} user roles")
    except Exception as e:
        logger.warning(f"RBAC: failed to load roles: {e}")


def get_user_role(email: str) -> dict | None:
    """Get user role from cache (refresh if stale)."""
    global _role_cache_ts
    if time.time() - _role_cache_ts > ROLE_CACHE_TTL:
        _load_roles()
    return _role_cache.get(email.lower().strip())


class RBACMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce role-based access on /api/* endpoints."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip RBAC for static files, health, and the index page
        if not path.startswith("/api/"):
            return await call_next(request)

        # /api/me is always allowed (it's how the frontend discovers the role)
        if path == "/api/me":
            return await call_next(request)

        # Extract user email from header (injected by Databricks Apps)
        email = request.headers.get("X-Forwarded-Email", "").lower().strip()

        # In local dev / no header → allow all (fall back to admin)
        if not email:
            request.state.user_role = {"persona": "support_centre_store", "store_filter": None, "division_filter": None, "is_admin": True}
            return await call_next(request)

        role = get_user_role(email)
        if not role:
            return JSONResponse(status_code=403, content={"error": "Access not configured. Contact your admin to get access to Larkwell Shelf Availability.", "email": email})

        request.state.user_role = role
        return await call_next(request)


app.add_middleware(RBACMiddleware)


def _actor(request: Request) -> str:
    """Who is using the app (injected by Databricks Apps); 'local' when running outside Databricks."""
    return request.headers.get("X-Forwarded-Email", "").lower().strip() or "local"


ALL_PERSONAS = ["support_centre", "retail"]
ALL_VIEWS = {
    "support_centre": ["store", "category"],
    "retail": ["regional_manager", "store_manager"],
}

def _compute_access(persona_str: str, is_admin: bool) -> dict:
    """Compute allowed_personas and allowed_views from role persona string."""
    if is_admin:
        return {"allowed_personas": ALL_PERSONAS[:], "allowed_views": {k: v[:] for k, v in ALL_VIEWS.items()},
                "default_persona": "support_centre", "default_view": "store"}

    # Persona string can be comma-separated for multi-persona access
    parts = [p.strip() for p in persona_str.split(",")]
    allowed_personas = []
    allowed_views = {}
    default_persona = None
    default_view = None

    for part in parts:
        if part in ("support_centre", "retail"):
            # Full persona access (both subviews)
            if part not in allowed_personas:
                allowed_personas.append(part)
            allowed_views[part] = ALL_VIEWS[part][:]
        elif part == "support_centre_store":
            if "support_centre" not in allowed_personas:
                allowed_personas.append("support_centre")
            allowed_views.setdefault("support_centre", [])
            if "store" not in allowed_views["support_centre"]:
                allowed_views["support_centre"].append("store")
        elif part == "support_centre_category":
            if "support_centre" not in allowed_personas:
                allowed_personas.append("support_centre")
            allowed_views.setdefault("support_centre", [])
            if "category" not in allowed_views["support_centre"]:
                allowed_views["support_centre"].append("category")
        elif part == "retail_store_manager":
            if "retail" not in allowed_personas:
                allowed_personas.append("retail")
            allowed_views.setdefault("retail", [])
            if "store_manager" not in allowed_views["retail"]:
                allowed_views["retail"].append("store_manager")
        elif part == "retail_regional":
            if "retail" not in allowed_personas:
                allowed_personas.append("retail")
            allowed_views.setdefault("retail", [])
            if "regional_manager" not in allowed_views["retail"]:
                allowed_views["retail"].append("regional_manager")

    # Default to first allowed
    if allowed_personas:
        default_persona = allowed_personas[0]
        default_view = allowed_views[default_persona][0] if allowed_views.get(default_persona) else "store"

    return {"allowed_personas": allowed_personas, "allowed_views": allowed_views,
            "default_persona": default_persona or "support_centre", "default_view": default_view or "store"}


@app.get("/api/me")
def get_me(request: Request):
    """Return current user's role, access config, and filters."""
    email = request.headers.get("X-Forwarded-Email", "").lower().strip()

    if not email:
        # Local dev / no header → return admin role
        access = _compute_access("support_centre", True)
        return {
            "email": "local-dev@larkwell.example",
            "is_admin": True,
            "store_filter": None,
            "division_filter": None,
            "authenticated": False,
            **access,
        }

    role = get_user_role(email)
    if not role:
        return JSONResponse(status_code=403, content={"error": "Access not configured. Contact your admin.", "email": email})

    access = _compute_access(role["persona"], role["is_admin"])
    return {
        "email": email,
        "is_admin": role["is_admin"],
        "store_filter": role["store_filter"],
        "division_filter": role["division_filter"],
        "authenticated": True,
        **access,
    }


# --- Column Mappings ---
STORE_AGG_COL = {
    "division": "division",
    "area": "area",
    "stg": "site_trading_group",
    "store": "store",
}
PRODUCT_AGG_COL = {
    "cluster": "cluster",
    "category": "category",
    "superGroup": "super_group",
    "productGroup": "product_group",
}


def _build_issue_filter(issue_filter: str, low_filter: str) -> str:
    """Build WHERE clause fragment for issue/low toggles."""
    if issue_filter == "gaps":
        return "issue = 'GAP'"
    elif issue_filter == "lows":
        if low_filter == "sales":
            return "issue = 'LOW' AND low_issue = 'SALES_LOW'"
        elif low_filter == "space":
            return "issue = 'LOW' AND low_issue = 'SPACE_LOW'"
        else:
            return "issue = 'LOW'"
    else:  # all
        if low_filter == "sales":
            return "(issue = 'GAP' OR (issue = 'LOW' AND low_issue = 'SALES_LOW'))"
        elif low_filter == "space":
            return "(issue = 'GAP' OR (issue = 'LOW' AND low_issue = 'SPACE_LOW'))"
        else:
            return "issue IN ('GAP', 'LOW')"


def _build_scope_filter(scope_filter: str) -> str:
    if scope_filter == "owned":
        return "business_scope = 'Owned'"
    elif scope_filter == "franchise":
        return "business_scope = 'Franchise'"
    return "1=1"


def _build_where(
    issue_filter: str = "all",
    low_filter: str = "both",
    scope_filter: str = "owned",
    division: str = "",
    area: str = "",
    stg: str = "",
    store: str = "",
    cluster: str = "",
    category: str = "",
    super_group: str = "",
    product_group: str = "",
    include_no_issue: bool = False,
) -> str:
    """Build complete WHERE clause."""
    parts = []
    parts.append(_build_scope_filter(scope_filter))
    if not include_no_issue:
        parts.append(_build_issue_filter(issue_filter, low_filter))
    if division:
        parts.append(f"division = '{_safe_str(division)}'")
    if area:
        parts.append(f"area = '{_safe_str(area)}'")
    if stg:
        parts.append(f"site_trading_group = '{_safe_str(stg)}'")
    if store:
        parts.append(f"store = '{_safe_str(store)}'")
    if cluster:
        parts.append(f"cluster = '{_safe_str(cluster)}'")
    if category:
        parts.append(f"category = '{_safe_str(category)}'")
    if super_group:
        parts.append(f"super_group = '{_safe_str(super_group)}'")
    if product_group:
        parts.append(f"product_group = '{_safe_str(product_group)}'")
    return " AND ".join(parts)


def _reason_col(persona: str) -> str:
    """Return the correct reason code column based on persona."""
    if persona in ("retail_regional", "retail_store_manager"):
        return "consensus_reason_retail"
    return "consensus_reason"


# --- API Endpoints ---

@app.get("/api/stores")
def get_stores(request: Request):
    role = getattr(request.state, "user_role", {})
    where = "1=1"
    if role.get("store_filter"):
        where = f"store = '{_safe_str(role['store_filter'])}'"
    elif role.get("division_filter"):
        where = f"division = '{_safe_str(role['division_filter'])}'"
    rows = execute_sql(f"SELECT DISTINCT store FROM {TABLE} WHERE {where} ORDER BY store")
    return {"stores": [r["store"] for r in rows]}


@app.get("/api/divisions")
def get_divisions(request: Request):
    role = getattr(request.state, "user_role", {})
    where = "division IS NOT NULL"
    if role.get("division_filter"):
        where += f" AND division = '{_safe_str(role['division_filter'])}'"
    rows = execute_sql(f"SELECT DISTINCT division, area FROM {TABLE} WHERE {where} ORDER BY division, area")
    divs = {}
    for r in rows:
        d = r["division"]
        if d not in divs:
            divs[d] = []
        divs[d].append(r["area"])
    return {"divisions": divs}


@app.get("/api/filters")
def get_filters():
    stgs = execute_sql(f"SELECT DISTINCT site_trading_group AS stg FROM {TABLE} WHERE site_trading_group IS NOT NULL ORDER BY stg")
    clusters = execute_sql(f"SELECT DISTINCT cluster FROM {TABLE} WHERE cluster IS NOT NULL ORDER BY cluster")
    categories = execute_sql(f"SELECT DISTINCT category FROM {TABLE} WHERE category IS NOT NULL ORDER BY category")
    divisions = execute_sql(f"SELECT DISTINCT division FROM {TABLE} WHERE division IS NOT NULL ORDER BY division")
    areas = execute_sql(f"SELECT DISTINCT area FROM {TABLE} WHERE area IS NOT NULL ORDER BY area")
    return {
        "stgs": [r["stg"] for r in stgs],
        "clusters": [r["cluster"] for r in clusters],
        "categories": [r["category"] for r in categories],
        "divisions": [r["division"] for r in divisions],
        "areas": [r["area"] for r in areas],
    }


@app.get("/api/dashboard")
def get_dashboard(
    persona: str = Query("support_centre_store", pattern="^(support_centre_store|support_centre_category|retail_regional|retail_store_manager)$"),
    issue_filter: str = Query("all", pattern="^(all|gaps|lows)$"),
    low_filter: str = Query("both", pattern="^(both|sales|space)$"),
    scope_filter: str = Query("owned", pattern="^(owned|franchise|all)$"),
    store_agg: str = Query("store", pattern="^(division|area|stg|store)$"),
    product_agg: str = Query("category", pattern="^(cluster|category|superGroup|productGroup)$"),
    division: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    store: Optional[str] = Query(None),
):
    """Main dashboard endpoint. Returns totals, reason breakdown, and aggregated table."""
    reason_col = _reason_col(persona)

    # Determine which aggregation level to show at top
    if persona in ("support_centre_store", "retail_regional"):
        agg_col_key = store_agg
        agg_col = STORE_AGG_COL.get(store_agg, "store")
    else:
        agg_col_key = product_agg
        agg_col = PRODUCT_AGG_COL.get(product_agg, "category")

    # Build WHERE for issues (filtered view)
    where_issues = _build_where(
        issue_filter=issue_filter, low_filter=low_filter, scope_filter=scope_filter,
        division=division or "", area=area or "", store=store or ""
    )

    # Build WHERE for total PLs (includes NO_ISSUE)
    where_all = _build_where(
        issue_filter="all", low_filter="both", scope_filter=scope_filter,
        division=division or "", area=area or "", store=store or "",
        include_no_issue=True
    )

    # Totals KPIs — total_pls from full scope, filtered counts from issue filter
    totals_sql = f"""
    SELECT
        (SELECT COUNT(*) FROM {TABLE} WHERE {where_all}) AS total_pls,
        COUNT(*) AS filtered_issues,
        SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) AS gaps,
        SUM(CASE WHEN issue='LOW' THEN 1 ELSE 0 END) AS lows,
        SUM(CASE WHEN low_issue='SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
        SUM(CASE WHEN low_issue='SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows,
        ROUND(SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END)*100.0/NULLIF((SELECT COUNT(*) FROM {TABLE} WHERE {where_all}),0), 2) AS pct_pls_gap,
        ROUND(COUNT(*)*100.0/NULLIF((SELECT COUNT(*) FROM {TABLE} WHERE {where_all}),0), 2) AS pct_pls_gap_low,
        SUM(CASE WHEN known_gap THEN 1 ELSE 0 END) AS known_gaps,
        SUM(CASE WHEN upstream_issue THEN 1 ELSE 0 END) AS upstream_count
    FROM {TABLE}
    WHERE {where_issues}
    """
    totals = execute_sql(totals_sql)

    # Reason code breakdown (only filtered issue rows)
    reason_sql = f"""
    SELECT {reason_col} AS reason_code, COUNT(*) AS count
    FROM {TABLE}
    WHERE {where_issues}
    GROUP BY {reason_col}
    ORDER BY count DESC
    """
    reasons = execute_sql(reason_sql)

    # --- Pivot mode for Head Office store view ---
    issue_cond = _build_issue_filter(issue_filter, low_filter)
    pivot_mode = persona == "support_centre_store"

    if pivot_mode:
        # Pivot table: reason code counts as columns
        agg_sql = f"""
        SELECT
            {agg_col} AS name,
            COUNT(*) AS total_pls,
            SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) AS grand_total,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'INVESTIGATE' THEN 1 ELSE 0 END) AS for_investigation,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'UNDER_FORECAST' THEN 1 ELSE 0 END) AS forecast,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'KNOWN_GAP' THEN 1 ELSE 0 END) AS known_gap,
            SUM(CASE WHEN {issue_cond} AND {reason_col} IN ('SUPPLIER_SHORT','SCARCITY') THEN 1 ELSE 0 END) AS low_depot_stock,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'ORDER_DELIVERY_BLOCK' THEN 1 ELSE 0 END) AS partially_supplied,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'STOCKFILE_ADJUSTMENT' THEN 1 ELSE 0 END) AS stockfile_adj,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'WASTE' THEN 1 ELSE 0 END) AS waste,
            SUM(CASE WHEN {issue_cond} AND {reason_col} NOT IN ('INVESTIGATE','UNDER_FORECAST','KNOWN_GAP','SUPPLIER_SHORT','SCARCITY','ORDER_DELIVERY_BLOCK','STOCKFILE_ADJUSTMENT','WASTE') THEN 1 ELSE 0 END) AS other
        FROM {TABLE}
        WHERE {where_all}
        GROUP BY {agg_col}
        HAVING SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) > 0
        ORDER BY SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) DESC
        LIMIT 100
        """
        agg_table = execute_sql(agg_sql)
        return {
            "totals": totals[0] if totals else {},
            "reasons": reasons,
            "table": agg_table,
            "pivot_mode": True,
        }

    # --- Standard mode for other personas ---
    agg_sql = f"""
    SELECT
        {agg_col} AS name,
        COUNT(*) AS total_pls,
        SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) AS filtered_issues,
        SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) AS gaps,
        SUM(CASE WHEN issue='LOW' THEN 1 ELSE 0 END) AS lows,
        SUM(CASE WHEN low_issue='SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
        SUM(CASE WHEN low_issue='SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows,
        ROUND(SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0), 2) AS pct_pls_gap,
        ROUND(SUM(CASE WHEN issue IN ('GAP','LOW') THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0), 2) AS pct_pls_gap_low
    FROM {TABLE}
    WHERE {where_all}
    GROUP BY {agg_col}
    HAVING SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) > 0
    ORDER BY SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) DESC
    LIMIT 100
    """
    agg_table = execute_sql(agg_sql)

    # Add reason breakdown per row for the aggregated table
    reason_by_agg_sql = f"""
    SELECT
        {agg_col} AS name,
        {reason_col} AS reason_code,
        COUNT(*) AS cnt,
        ROUND(COUNT(*)*100.0 / SUM(COUNT(*)) OVER(PARTITION BY {agg_col}), 1) AS pct
    FROM {TABLE}
    WHERE {where_issues}
    GROUP BY {agg_col}, {reason_col}
    ORDER BY {agg_col}, cnt DESC
    """
    reason_by_agg = execute_sql(reason_by_agg_sql)

    # Group reasons by agg name
    reason_map = {}
    for r in reason_by_agg:
        name = r["name"]
        if name not in reason_map:
            reason_map[name] = []
        reason_map[name].append({"code": r["reason_code"], "count": r["cnt"], "pct": r["pct"]})

    # Attach reasons to agg_table rows
    for row in agg_table:
        row["reasons"] = reason_map.get(row["name"], [])

    return {
        "totals": totals[0] if totals else {},
        "reasons": reasons,
        "table": agg_table,
    }


@app.get("/api/drill")
def get_drill(
    persona: str = Query("support_centre_store"),
    issue_filter: str = Query("all", pattern="^(all|gaps|lows)$"),
    low_filter: str = Query("both", pattern="^(both|sales|space)$"),
    scope_filter: str = Query("owned", pattern="^(owned|franchise|all)$"),
    drill_dimension: str = Query("store"),
    division: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    stg: Optional[str] = Query(None),
    store: Optional[str] = Query(None),
    cluster: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    super_group: Optional[str] = Query(None),
    product_group: Optional[str] = Query(None),
    product_agg: str = Query("category", pattern="^(cluster|category|superGroup|productGroup)$"),
    store_agg: str = Query("store", pattern="^(division|area|stg|store)$"),
):
    """Drill-down endpoint. Returns aggregated or terminal data based on drill_dimension."""
    reason_col = _reason_col(persona)

    pivot_mode = persona == "support_centre_store"

    # Determine column to group by
    if drill_dimension == "product":
        # Terminal level
        where_issues = _build_where(
            issue_filter=issue_filter, low_filter=low_filter, scope_filter=scope_filter,
            division=division or "", area=area or "", stg=stg or "",
            store=store or "", cluster=cluster or "", category=category or "",
            super_group=super_group or "", product_group=product_group or ""
        )
        where_all_terminal = _build_where(
            issue_filter="all", low_filter="both", scope_filter=scope_filter,
            division=division or "", area=area or "", stg=stg or "",
            store=store or "", cluster=cluster or "", category=category or "",
            super_group=super_group or "", product_group=product_group or "",
            include_no_issue=True
        )
        issue_cond = _build_issue_filter(issue_filter, low_filter)

        if pivot_mode:
            # Pivot terminal: product rows with reason code columns
            sql = f"""
            SELECT
                product, upc, store,
                SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) AS grand_total,
                SUM(CASE WHEN {issue_cond} AND {reason_col} = 'INVESTIGATE' THEN 1 ELSE 0 END) AS for_investigation,
                SUM(CASE WHEN {issue_cond} AND {reason_col} = 'UNDER_FORECAST' THEN 1 ELSE 0 END) AS forecast,
                SUM(CASE WHEN {issue_cond} AND {reason_col} = 'KNOWN_GAP' THEN 1 ELSE 0 END) AS known_gap,
                SUM(CASE WHEN {issue_cond} AND {reason_col} IN ('SUPPLIER_SHORT','SCARCITY') THEN 1 ELSE 0 END) AS low_depot_stock,
                SUM(CASE WHEN {issue_cond} AND {reason_col} = 'ORDER_DELIVERY_BLOCK' THEN 1 ELSE 0 END) AS partially_supplied,
                SUM(CASE WHEN {issue_cond} AND {reason_col} = 'STOCKFILE_ADJUSTMENT' THEN 1 ELSE 0 END) AS stockfile_adj,
                SUM(CASE WHEN {issue_cond} AND {reason_col} = 'WASTE' THEN 1 ELSE 0 END) AS waste,
                SUM(CASE WHEN {issue_cond} AND {reason_col} NOT IN ('INVESTIGATE','UNDER_FORECAST','KNOWN_GAP','SUPPLIER_SHORT','SCARCITY','ORDER_DELIVERY_BLOCK','STOCKFILE_ADJUSTMENT','WASTE') THEN 1 ELSE 0 END) AS other
            FROM {TABLE}
            WHERE {where_all_terminal}
            GROUP BY product, upc, store
            HAVING SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) > 0
            ORDER BY SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) DESC
            LIMIT 200
            """
            items = execute_sql(sql)
            summary_sql = f"""
            SELECT COUNT(*) AS total_pls,
                SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) AS gaps,
                SUM(CASE WHEN issue='LOW' THEN 1 ELSE 0 END) AS lows,
                SUM(CASE WHEN low_issue='SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
                SUM(CASE WHEN low_issue='SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows
            FROM {TABLE}
            WHERE {where_all_terminal}
            """
            summary = execute_sql(summary_sql)
            return {"items": items, "summary": summary[0] if summary else {}, "terminal": True, "pivot_mode": True}

        # Standard terminal: product-location rows
        sql = f"""
        SELECT
            product, upc, store, category, super_group, product_group,
            issue, low_issue, {reason_col} AS reason_code,
            known_gap, supplier_short, supplier_short_type,
            COALESCE(supplier_short_qty, 0) AS supplier_short_qty,
            scarcity, COALESCE(scarcity_qty, 0) AS scarcity_qty,
            waste, COALESCE(waste_qty, 0) AS waste_qty,
            under_forecast, COALESCE(under_forecast_qty, 0) AS under_forecast_qty,
            COALESCE(under_space_qty, 0) AS under_space_qty,
            COALESCE(stockfile_adjustment_qty, 0) AS stockfile_adjustment_qty,
            elimination, msc_decrease, upstream_issue,
            supplier, depot, division, area, site_trading_group
        FROM {TABLE}
        WHERE {where_issues}
        ORDER BY COALESCE(supplier_short_qty,0)+COALESCE(scarcity_qty,0)+COALESCE(waste_qty,0)+COALESCE(under_forecast_qty,0) DESC
        LIMIT 200
        """
        items = execute_sql(sql)
        summary_sql = f"""
        SELECT COUNT(*) AS total_pls,
            SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) AS gaps,
            SUM(CASE WHEN issue='LOW' THEN 1 ELSE 0 END) AS lows,
            SUM(CASE WHEN low_issue='SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
            SUM(CASE WHEN low_issue='SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows
        FROM {TABLE}
        WHERE {where_all_terminal}
        """
        summary = execute_sql(summary_sql)
        return {"items": items, "summary": summary[0] if summary else {}, "terminal": True}

    # Aggregated level
    if drill_dimension in STORE_AGG_COL:
        agg_col = STORE_AGG_COL[drill_dimension]
    elif drill_dimension in PRODUCT_AGG_COL:
        agg_col = PRODUCT_AGG_COL[drill_dimension]
    else:
        agg_col = drill_dimension

    where_all = _build_where(
        issue_filter="all", low_filter="both", scope_filter=scope_filter,
        division=division or "", area=area or "", stg=stg or "",
        store=store or "", cluster=cluster or "", category=category or "",
        super_group=super_group or "", product_group=product_group or "",
        include_no_issue=True
    )
    where_issues = _build_where(
        issue_filter=issue_filter, low_filter=low_filter, scope_filter=scope_filter,
        division=division or "", area=area or "", stg=stg or "",
        store=store or "", cluster=cluster or "", category=category or "",
        super_group=super_group or "", product_group=product_group or ""
    )
    issue_cond = _build_issue_filter(issue_filter, low_filter)

    if pivot_mode:
        # Pivot intermediate level: reason code columns
        agg_sql = f"""
        SELECT
            {agg_col} AS name,
            COUNT(*) AS total_pls,
            SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) AS grand_total,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'INVESTIGATE' THEN 1 ELSE 0 END) AS for_investigation,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'UNDER_FORECAST' THEN 1 ELSE 0 END) AS forecast,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'KNOWN_GAP' THEN 1 ELSE 0 END) AS known_gap,
            SUM(CASE WHEN {issue_cond} AND {reason_col} IN ('SUPPLIER_SHORT','SCARCITY') THEN 1 ELSE 0 END) AS low_depot_stock,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'ORDER_DELIVERY_BLOCK' THEN 1 ELSE 0 END) AS partially_supplied,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'STOCKFILE_ADJUSTMENT' THEN 1 ELSE 0 END) AS stockfile_adj,
            SUM(CASE WHEN {issue_cond} AND {reason_col} = 'WASTE' THEN 1 ELSE 0 END) AS waste,
            SUM(CASE WHEN {issue_cond} AND {reason_col} NOT IN ('INVESTIGATE','UNDER_FORECAST','KNOWN_GAP','SUPPLIER_SHORT','SCARCITY','ORDER_DELIVERY_BLOCK','STOCKFILE_ADJUSTMENT','WASTE') THEN 1 ELSE 0 END) AS other
        FROM {TABLE}
        WHERE {where_all}
        GROUP BY {agg_col}
        HAVING SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) > 0
        ORDER BY SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) DESC
        LIMIT 100
        """
        items = execute_sql(agg_sql)
        summary_sql = f"""
        SELECT COUNT(*) AS total_pls,
            SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) AS gaps,
            SUM(CASE WHEN issue='LOW' THEN 1 ELSE 0 END) AS lows,
            SUM(CASE WHEN low_issue='SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
            SUM(CASE WHEN low_issue='SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows
        FROM {TABLE}
        WHERE {where_all}
        """
        summary = execute_sql(summary_sql)
        return {"items": items, "summary": summary[0] if summary else {}, "terminal": False, "pivot_mode": True}

    # Standard aggregated level (other personas)
    agg_sql = f"""
    SELECT
        {agg_col} AS name,
        COUNT(*) AS total_pls,
        SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) AS filtered_issues,
        SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) AS gaps,
        SUM(CASE WHEN issue='LOW' THEN 1 ELSE 0 END) AS lows,
        SUM(CASE WHEN low_issue='SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
        SUM(CASE WHEN low_issue='SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows,
        ROUND(SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0), 2) AS pct_pls_gap,
        ROUND(SUM(CASE WHEN issue IN ('GAP','LOW') THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0), 2) AS pct_pls_gap_low
    FROM {TABLE}
    WHERE {where_all}
    GROUP BY {agg_col}
    HAVING SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) > 0
    ORDER BY SUM(CASE WHEN {issue_cond} THEN 1 ELSE 0 END) DESC
    LIMIT 100
    """
    items = execute_sql(agg_sql)

    # Reason breakdown per agg item
    reason_sql = f"""
    SELECT {agg_col} AS name, {reason_col} AS reason_code, COUNT(*) AS cnt,
        ROUND(COUNT(*)*100.0 / SUM(COUNT(*)) OVER(PARTITION BY {agg_col}), 1) AS pct
    FROM {TABLE}
    WHERE {where_issues}
    GROUP BY {agg_col}, {reason_col}
    ORDER BY {agg_col}, cnt DESC
    """
    reason_rows = execute_sql(reason_sql)
    reason_map = {}
    for r in reason_rows:
        name = r["name"]
        if name not in reason_map:
            reason_map[name] = []
        reason_map[name].append({"code": r["reason_code"], "count": r["cnt"], "pct": r["pct"]})
    for item in items:
        item["reasons"] = reason_map.get(item["name"], [])

    # Summary totals — total_pls is full scope, gaps/lows filtered
    summary_sql = f"""
    SELECT COUNT(*) AS total_pls,
        SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) AS gaps,
        SUM(CASE WHEN issue='LOW' THEN 1 ELSE 0 END) AS lows,
        SUM(CASE WHEN low_issue='SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
        SUM(CASE WHEN low_issue='SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows,
        ROUND(SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0), 2) AS pct_pls_gap,
        ROUND(SUM(CASE WHEN issue IN ('GAP','LOW') THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0), 2) AS pct_pls_gap_low
    FROM {TABLE}
    WHERE {where_all}
    """
    summary = execute_sql(summary_sql)

    return {"items": items, "summary": summary[0] if summary else {}, "terminal": False}


# --- Morning Briefing ---
@app.get("/api/store-briefing/{store_name}")
def get_store_briefing(store_name: str, persona: str = Query("support_centre_store")):
    safe = _safe_str(store_name)
    reason_col = _reason_col(persona)

    # Total PLs and issue breakdown for this store
    kpi_sql = f"""
    SELECT
        COUNT(*) AS total_pls,
        SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) AS gaps,
        SUM(CASE WHEN issue='LOW' THEN 1 ELSE 0 END) AS lows,
        SUM(CASE WHEN low_issue='SALES_LOW' THEN 1 ELSE 0 END) AS sales_lows,
        SUM(CASE WHEN low_issue='SPACE_LOW' THEN 1 ELSE 0 END) AS space_lows,
        ROUND(SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS pct_pls_gap,
        ROUND(SUM(CASE WHEN issue IN ('GAP','LOW') THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS pct_pls_gap_low,
        SUM(CASE WHEN known_gap THEN 1 ELSE 0 END) AS known_gap_count,
        SUM(CASE WHEN waste THEN 1 ELSE 0 END) AS waste_count,
        SUM(COALESCE(waste_qty, 0)) AS total_waste_qty,
        SUM(CASE WHEN scarcity THEN 1 ELSE 0 END) AS scarcity_count,
        SUM(CASE WHEN supplier_short THEN 1 ELSE 0 END) AS supplier_short_count,
        SUM(CASE WHEN upstream_issue THEN 1 ELSE 0 END) AS upstream_count,
        SUM(CASE WHEN order_delivery_block THEN 1 ELSE 0 END) AS block_count,
        COUNT(DISTINCT category) AS category_count,
        COUNT(DISTINCT supplier) AS supplier_count
    FROM {TABLE}
    WHERE store = '{safe}'
    """
    kpis = execute_sql(kpi_sql)
    kpi = kpis[0] if kpis else {}

    # Reason code breakdown
    reason_sql = f"""
    SELECT {reason_col} AS reason_code, COUNT(*) AS count,
        ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 1) AS pct
    FROM {TABLE}
    WHERE store = '{safe}' AND issue != 'NO_ISSUE'
    GROUP BY {reason_col}
    ORDER BY count DESC
    """
    reasons = execute_sql(reason_sql)

    # Category × Reason Code pivot (for category breakdown table)
    cat_reason_sql = f"""
    SELECT category,
        SUM(CASE WHEN {reason_col} = 'INVESTIGATE' THEN 1 ELSE 0 END) AS for_investigation,
        SUM(CASE WHEN {reason_col} = 'UNDER_FORECAST' THEN 1 ELSE 0 END) AS forecast,
        SUM(CASE WHEN {reason_col} = 'KNOWN_GAP' THEN 1 ELSE 0 END) AS known_gap,
        SUM(CASE WHEN {reason_col} IN ('SUPPLIER_SHORT', 'SCARCITY') THEN 1 ELSE 0 END) AS low_depot_stock,
        SUM(CASE WHEN {reason_col} IN ('ORDER_DELIVERY_BLOCK', 'UPSTREAM_ISSUE') THEN 1 ELSE 0 END) AS partially_supplied,
        SUM(CASE WHEN {reason_col} = 'STOCKFILE_ADJUSTMENT' THEN 1 ELSE 0 END) AS stockfile_adjustment,
        SUM(CASE WHEN {reason_col} = 'WASTE' THEN 1 ELSE 0 END) AS waste,
        SUM(CASE WHEN {reason_col} NOT IN ('INVESTIGATE','UNDER_FORECAST','KNOWN_GAP','SUPPLIER_SHORT','SCARCITY','ORDER_DELIVERY_BLOCK','UPSTREAM_ISSUE','STOCKFILE_ADJUSTMENT','WASTE') THEN 1 ELSE 0 END) AS other,
        COUNT(*) AS grand_total
    FROM {TABLE}
    WHERE store = '{safe}' AND issue != 'NO_ISSUE'
    GROUP BY category
    ORDER BY grand_total DESC
    """
    category_reason_breakdown = execute_sql(cat_reason_sql)

    return {
        "store_name": store_name,
        "kpis": kpi,
        "reasons": reasons,
        "category_reason_breakdown": category_reason_breakdown,
    }


# --- Chat ---
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    store_name: Optional[str] = None


class FeedbackRequest(BaseModel):
    conversation_id: str
    message_id: str
    is_positive: bool
    comment: Optional[str] = ""
    question: Optional[str] = ""
    answer: Optional[str] = ""
    sql: Optional[str] = ""


# --- Pinned deep-reasoning Q&A for the AI Chat (STORE-AWARE, grounded live in rca_gap_agg_v4) ---
_REASON_LABEL = {
    "SUPPLIER_SHORT": "Supplier short", "UNDER_FORECAST": "Under-forecast",
    "ORDER_DELIVERY_BLOCK": "Order/delivery block", "STOCKFILE_ADJUSTMENT": "Stockfile adjustment",
    "SCARCITY": "Scarcity", "WASTE": "Waste", "KNOWN_GAP": "Known gap",
    "ELIMINATION": "Elimination", "MSC_DECREASE": "Range reduction",
    "UNDER_SPACE": "Under-space", "INVESTIGATE": "Investigate",
}
_SHORT_ACTION = {
    "SUPPLIER_SHORT": "Chase depot; raise shortage claim", "UNDER_FORECAST": "Raise today's order",
    "ORDER_DELIVERY_BLOCK": "Expedite the stuck order", "STOCKFILE_ADJUSTMENT": "Cycle-count; correct book stock",
    "SCARCITY": "Offer an approved alternative", "WASTE": "Check date-code; trim the order",
    "INVESTIGATE": "Flag for the analyst",
}
_OWNER = {
    "SUPPLIER_SHORT": "Central buying", "UNDER_FORECAST": "Demand planning + store",
    "ORDER_DELIVERY_BLOCK": "Logistics + store", "STOCKFILE_ADJUSTMENT": "**Store team**",
    "SCARCITY": "Market (none)", "WASTE": "Store + buying", "KNOWN_GAP": "Range team",
    "INVESTIGATE": "Availability analyst",
}
_OPPORTUNITY = {
    "SUPPLIER_SHORT": "Buying chases the top suppliers", "UNDER_FORECAST": "Store raises local orders",
    "ORDER_DELIVERY_BLOCK": "Depot releases stuck orders", "STOCKFILE_ADJUSTMENT": "Cycle-count - a pure store fix",
    "SCARCITY": "Not controllable - market-wide", "WASTE": "Tighten ordering and handling",
    "KNOWN_GAP": "Filter out - not a failure", "INVESTIGATE": "Assign for investigation",
}
def _risk_window(days_of_cover):
    """When the shelf empties at today's forecast demand: stock on hand divided by forecast, from the gold table."""
    d = float(days_of_cover or 0)
    if d < 0.5:
        return "Before midday"
    if d < 1:
        return "Today"
    if d < 2:
        return "Tomorrow"
    return "This week"


def _clean_prod(p):
    return (p or "").strip()


# Q1 is a demand/run-out question, so it only surfaces demand-driven signals (not supply-admin
# reasons like Investigate / Order-delivery-block) and gives peak-prep actions.
_Q1_REASON = {
    "SALES_FAST": "Selling fast - low on shelf",
    "UNDER_FORECAST": "Demand ahead of forecast",
    "SUPPLIER_SHORT": "Demand outpacing supply",
}
_Q1_ACTION = {
    "SALES_FAST": "Replenish from back-stock now; lift the replen multiple before the rush",
    "UNDER_FORECAST": "Raise today's order; top up the shelf ahead of the peak",
    "SUPPLIER_SHORT": "Pull the depot top-up forward; face up remaining stock",
}


def _pin_watchlist(store):
    """Lines still on the shelf but below their minimum display, most urgent first (fewest days of cover)."""
    risk_case = ("CASE WHEN consensus_reason='UNDER_FORECAST' THEN 'UNDER_FORECAST' "
                 "WHEN consensus_reason='SUPPLIER_SHORT' THEN 'SUPPLIER_SHORT' ELSE 'SALES_FAST' END")
    cond = ("issue='LOW' AND consensus_reason <> 'KNOWN_GAP' "
            "AND (low_issue='SALES_LOW' OR consensus_reason IN ('UNDER_FORECAST','SUPPLIER_SHORT'))")
    cols = "product, category, days_of_cover, on_hand_units, forecast_units" + ("" if store else ", store")
    store_filter = f"store='{_safe_str(store)}' AND " if store else ""
    rows = execute_sql(f"SELECT {cols}, {risk_case} AS risk_type FROM {TABLE} WHERE {store_filter}{cond} "
                       f"ORDER BY days_of_cover ASC, forecast_units DESC, product LIMIT 6")
    scope = f"**{store}**" if store else "the estate"
    if not rows:
        return f"Good news - nothing at {scope} is trending to run out before the next peak right now."
    hdr = "| Product | Category | Runs out | Why it's at risk | Act now |" if store else "| Product · Store | Category | Runs out | Why it's at risk | Act now |"
    out = [hdr, "|---|---|---|---|---|"]
    for r in rows:
        rt = r.get("risk_type") or "SALES_FAST"
        name = _clean_prod(r.get("product"))
        if not store:
            name = f"{name} · {r.get('store') or ''}"
        left, fc = int(float(r.get("on_hand_units") or 0)), int(float(r.get("forecast_units") or 0))
        window = f"{_risk_window(r.get('days_of_cover'))} ({left} left, {fc} forecast)"
        out.append(f"| {name} | {r.get('category') or ''} | {window} | {_Q1_REASON.get(rt, 'Selling fast')} | {_Q1_ACTION.get(rt, 'Replenish from back-stock now')} |")
    table = "\n".join(out)
    return (f"Here's the at-risk watchlist for {scope}: lines still on the shelf but below their minimum display, most urgent first. "
            f"'Runs out' is the stock on hand divided by today's forecast.\n\n{table}")


def _pin_action_queue(store):
    qty = "GREATEST(COALESCE(supplier_short_qty,0),COALESCE(under_forecast_qty,0),COALESCE(stockfile_adjustment_qty,0))"
    cond = "issue='GAP' AND consensus_reason IN ('SUPPLIER_SHORT','UNDER_FORECAST','ORDER_DELIVERY_BLOCK','STOCKFILE_ADJUSTMENT')"
    if store:
        rows = execute_sql(f"SELECT product, consensus_reason, supplier, {qty} qty FROM {TABLE} WHERE store='{_safe_str(store)}' AND {cond} ORDER BY qty DESC LIMIT 5")
        scope = f"**{store}**"
    else:
        rows = execute_sql(f"SELECT product, store, consensus_reason, supplier, {qty} qty FROM {TABLE} WHERE {cond} ORDER BY qty DESC LIMIT 5")
        scope = "the estate"
    if not rows:
        return f"Good news - no high-impact actionable gaps at {scope} right now."
    hdr = "| # | Product | Evidence | Action |" if store else "| # | Product · Store | Evidence | Action |"
    out = [hdr, "|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        rc = r.get("consensus_reason") or "INVESTIGATE"
        name = _clean_prod(r.get("product"))
        if not store:
            name = f"{name} · {r.get('store') or ''}"
        qv = int(float(r.get("qty") or 0))
        sup = r.get("supplier") or ""
        ev = f"{_REASON_LABEL.get(rc, rc)} ~{qv}u" + (f" ({sup})" if sup else "")
        out.append(f"| {i} | {name} | {ev} | {_SHORT_ACTION.get(rc, 'Review and act')} |")
    table = "\n".join(out)
    return f"Here's the ranked action queue for {scope} (next hour) - highest-impact actionable gaps first:\n\n{table}"


def _pin_peer_compare(store):
    base = f"WITH s AS (SELECT site_trading_group stg, store, COUNT(*) pls, SUM(CASE WHEN issue='GAP' THEN 1 ELSE 0 END) gaps FROM {TABLE} GROUP BY site_trading_group, store), r AS (SELECT stg, store, ROUND(100.0*gaps/pls,1) gr, ROUND(AVG(100.0*gaps/pls) OVER (PARTITION BY stg),1) pa, gaps FROM s)"
    if not store:
        pick = execute_sql(f"{base} SELECT store FROM r WHERE gaps>120 ORDER BY (gr-pa) DESC LIMIT 1")
        store = pick[0]["store"] if pick else None
        if not store:
            return "Select a store from the sidebar and I'll compare it to its peer group."
    stat = execute_sql(f"{base} SELECT stg, gr, pa, gaps FROM r WHERE store='{_safe_str(store)}'")
    if not stat:
        return f"I couldn't find availability data for {store}."
    st = stat[0]
    gr = float(st.get("gr") or 0); pa = float(st.get("pa") or 0); gaps = int(float(st.get("gaps") or 0)); stg = st.get("stg") or "comparable"
    mix = execute_sql(f"SELECT consensus_reason, COUNT(*) n, ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER(),0) pct FROM {TABLE} WHERE store='{_safe_str(store)}' AND issue='GAP' GROUP BY consensus_reason ORDER BY n DESC LIMIT 5")
    out = ["| Driver | Share of gaps | Who owns it | Opportunity |", "|---|---|---|---|"]
    for m in mix:
        rc = m.get("consensus_reason") or "INVESTIGATE"
        out.append(f"| {_REASON_LABEL.get(rc, rc)} | {int(float(m.get('pct') or 0))}% | {_OWNER.get(rc, 'Buying')} | {_OPPORTUNITY.get(rc, 'Review')} |")
    table = "\n".join(out)
    ratio = round(gr / pa, 1) if pa else 0
    if gr > pa * 1.1:
        verdict = (f"**{store}'s gap rate is {gr}% versus {pa}% for comparable {stg} stores** - about {ratio}x its peers "
                   f"({gaps} gaps). A lot of that isn't the store team's fault, and the rest is very actionable:")
    elif gr < pa * 0.9:
        verdict = (f"Good story: **{store} is actually ahead of its peers** - a {gr}% gap rate versus {pa}% for comparable {stg} stores ({gaps} gaps). Where it does gap, the drivers are:")
    else:
        verdict = (f"**{store} is broadly in line with its peers** - a {gr}% gap rate versus {pa}% for comparable {stg} stores ({gaps} gaps). The drivers are:")
    return f"Here's the adjusted peer read for **{store}** ({stg}).\n\n{verdict}\n\n{table}"


PINNED_QA = [
    {"q": "Which products are likely to run out before the next lunch or evening peak - and what can we do now?", "fn": _pin_watchlist},
    {"q": "Which availability issues should we fix in the next hour to protect the most profitable sales?", "fn": _pin_action_queue},
    {"q": "Why is this store performing worse than comparable stores, and what can its team actually control?", "fn": _pin_peer_compare},
]


def _norm_q(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


_PINNED_INDEX = {_norm_q(x["q"]): x["fn"] for x in PINNED_QA}


def _match_pinned(message):
    return _PINNED_INDEX.get(_norm_q(message))


@app.get("/api/suggested-questions")
def api_suggested_questions():
    return {"questions": [x["q"] for x in PINNED_QA]}


@app.post("/api/chat")
def chat(req: ChatRequest, request: Request):
    _fn = _match_pinned(req.message)
    if _fn is not None:
        # Curated analysis: a fixed, tested SQL analysis run live on today's gold table. It is not a Genie answer,
        # and the app labels it as such.
        try:
            _text = _fn(req.store_name)       # store-aware: tailored to the selected store
        except Exception as e:
            logger.warning(f"curated analysis failed: {e}")
            _text = "Sorry - I couldn't pull that just now. Please try again."
        return {"text": _text, "conversation_id": req.conversation_id, "source": "curated"}
    if not GENIE_SPACE_ID:
        return {"text": "Chat is not configured yet. Genie Space ID needs to be set.", "conversation_id": None}

    question = req.message
    if req.store_name:
        question = f"For store {req.store_name}: {question}"

    host = _get_host()
    headers = _headers()

    try:
        # Retry logic for 429 rate limits (up to 2 retries with backoff)
        r = None
        for attempt in range(3):
            if req.conversation_id:
                r = requests.post(
                    f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{req.conversation_id}/messages",
                    json={"content": question}, headers=headers, timeout=120,
                )
            else:
                r = requests.post(
                    f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation",
                    json={"content": question}, headers=headers, timeout=120,
                )
            if r.status_code == 429 and attempt < 2:
                wait = int(r.headers.get("Retry-After", 15)) if attempt == 0 else 30
                logger.warning(f"Genie rate limited (429), retrying in {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
                continue
            break

        if r.status_code == 429:
            return {"text": "The AI assistant is currently busy. Please wait a moment and try again.", "conversation_id": req.conversation_id}
        if r.status_code != 200:
            return {"text": f"Error communicating with Genie: {r.status_code}", "conversation_id": req.conversation_id}

        resp = r.json()
        conv_id = resp.get("conversation_id", "")
        msg_id = resp.get("message_id", "")

        # Poll for completion
        start = time.time()
        while time.time() - start < 90:
            r2 = requests.get(
                f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conv_id}/messages/{msg_id}",
                headers=headers, timeout=30,
            )
            if r2.status_code != 200:
                break
            raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', r2.text)
            msg = json.loads(raw)
            status = msg.get("status", "")
            if status == "COMPLETED":
                attachments = msg.get("attachments", [])
                answer_text = ""
                table_data = None
                sql_text = ""
                for att in attachments:
                    if att.get("text"):
                        answer_text = att["text"].get("content", "")
                    if att.get("query"):
                        sql_text = att["query"].get("query", "")
                        att_id = att.get("attachment_id") or att.get("id")
                        qr_resp = requests.get(
                            f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conv_id}/messages/{msg_id}"
                            f"/attachments/{att_id}/query-result",
                            headers=headers, timeout=30,
                        )
                        if qr_resp.status_code == 200:
                            qr = json.loads(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', qr_resp.text))
                            sr = qr.get("statement_response", qr)
                            cols = [c.get("name", f"col{i}") for i, c in enumerate(sr.get("manifest", {}).get("schema", {}).get("columns", []))]
                            rows_data = sr.get("result", {}).get("data_array", []) or []
                            table_data = {"columns": cols, "rows": rows_data[:50]}
                result = {
                    "text": answer_text or "Query executed successfully.",
                    "columns": table_data["columns"] if table_data else None,
                    "rows": table_data["rows"] if table_data else None,
                    "conversation_id": conv_id,
                    "message_id": msg_id,
                    "sql": sql_text,
                    "source": "genie",
                }
                # Log the answer to Lakebase (never slows the reply)
                _log_conversation_async(question, result, _actor(request))
                return result
            elif status in ("FAILED", "CANCELLED"):
                return {"text": "I wasn't able to generate a response. Please try rephrasing.", "conversation_id": conv_id}
            time.sleep(2)

        return {"text": "Response timed out. Please try again.", "conversation_id": conv_id}

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"text": f"Error: {str(e)}", "conversation_id": req.conversation_id}


# --- Feedback: Genie's own feedback API, plus a copy in Lakebase that Lakehouse Sync brings back to UC ---

def _log_conversation_async(question: str, result: dict, actor: str = ""):
    """Log every Genie answer (no rating yet). Fire-and-forget, so it never slows the reply."""
    lakebase.log_feedback(result.get("message_id", ""), result.get("conversation_id", ""), None, None,
                          question, result.get("text", ""), result.get("sql", ""), actor)


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest, request: Request):
    """Thumbs up or down: sent to Genie's feedback API and recorded in Lakebase."""
    rating = "POSITIVE" if req.is_positive else "NEGATIVE"
    try:
        resp = requests.post(
            f"{_get_host()}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{req.conversation_id}/messages/{req.message_id}/feedback",
            headers=_headers(), json={"rating": rating}, timeout=15,
        )
        logger.info(f"Genie feedback API: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Genie feedback API failed: {e}")
    lakebase.log_feedback(req.message_id, req.conversation_id, req.is_positive, req.comment or "",
                          req.question or "", req.answer or "", req.sql or "", _actor(request))
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    def _warm():
        logger.info(f"Lakebase warm-up: {lakebase.health()}")
    threading.Thread(target=_warm, daemon=True).start()


# --- Shelf Scan (SST): barcode/UPC scan -> STATUS + REASON CODE, served from Lakebase ---
LLM_ENDPOINT = os.getenv("SERVING_ENDPOINT_NAME", "databricks-claude-sonnet-4-5")

_QTY_BY_REASON = {
    "SUPPLIER_SHORT": ("supplier_short_qty", "Units short"),
    "SCARCITY": ("scarcity_qty", "Units cut from allocation"),
    "WASTE": ("waste_qty", "Units wasted"),
    "UNDER_FORECAST": ("under_forecast_qty", "Units above forecast"),
    "STOCKFILE_ADJUSTMENT": ("stockfile_adjustment_qty", "Phantom units found"),
}

# What a colleague can record against each root cause. The server checks the action type against this list.
ACTION_OPTIONS = {
    "SUPPLIER_SHORT": [("RAISED_SHORTAGE_QUERY", "Raised shortage query"), ("FILLED_FROM_STOCKROOM", "Filled from stockroom")],
    "ORDER_DELIVERY_BLOCK": [("CHASED_BLOCKED_ORDER", "Chased blocked order")],
    "STOCKFILE_ADJUSTMENT": [("CORRECTED_STOCK_FILE", "Counted and corrected stock file")],
    "UNDER_FORECAST": [("RAISED_ORDER", "Raised today's order")],
    "WASTE": [("CHECKED_DATE_CODES", "Checked date codes"), ("REQUESTED_ORDER_REVIEW", "Asked for order review")],
    "SCARCITY": [("FILLED_WITH_ALTERNATIVE", "Filled with approved alternative")],
    "KNOWN_GAP": [("CONFIRMED_PLANNED_GAP", "Confirmed planned gap")],
    "INVESTIGATE": [("ESCALATED_TO_ANALYST", "Escalated to analyst")],
}
_VALID_ACTIONS = {t for opts in ACTION_OPTIONS.values() for t, _ in opts}


def call_llm(messages: list) -> str:
    host = _get_host()
    try:
        r = requests.post(
            f"{host}/serving-endpoints/{LLM_ENDPOINT}/invocations",
            headers=_headers(), json={"messages": messages, "max_tokens": 220}, timeout=30,
        )
        if r.status_code != 200:
            logger.warning(f"LLM {r.status_code}: {r.text[:150]}")
            return ""
        content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            return _clean("\n".join(b.get("text", "") for b in content if b.get("type") == "text"))
        return _clean(content) if isinstance(content, str) else ""
    except Exception as e:
        logger.warning(f"LLM error: {e}")
        return ""


def _scan_row(store, upc, source):
    """One product-location for Shelf Scan: Lakebase first, the SQL warehouse if Lakebase can't answer."""
    if source == "lakebase":
        try:
            row, ms = lakebase.lookup(store, upc)
            return row, "lakebase", ms
        except Exception as e:
            logger.warning(f"Lakebase lookup failed, using the warehouse: {e}")
    t0 = time.perf_counter()
    rows = execute_sql(f"SELECT {lakebase.SCAN_COLUMNS} FROM {TABLE} "
                       f"WHERE store = '{_safe_str(store)}' AND upc = '{_safe_str(upc)}' LIMIT 1")
    return (rows[0] if rows else None), "warehouse", (time.perf_counter() - t0) * 1000


@app.get("/api/sst-lookup")
def api_sst_lookup(store: str, upc: str, request: Request,
                   source: str = Query("lakebase", pattern="^(lakebase|warehouse)$")):
    """Shelf Scan -> product's availability STATUS + REASON CODE."""
    t0 = time.perf_counter()
    r, served_by, db_ms = _scan_row(store, upc, source)
    timing = {"served_by": served_by, "lookup_ms": round(db_ms, 1), "total_ms": round((time.perf_counter() - t0) * 1000, 1)}
    actor = _actor(request)
    if not r:
        lakebase.log_scan(store, upc, "NOT_FOUND", None, None, served_by, db_ms, actor)
        return {"status": "NOT_FOUND", "message": f"UPC {upc} is not ranged at {store}.",
                "store": store, "upc": upc, **timing}
    issue = r.get("issue") or "NO_ISSUE"
    product = r.get("product") or upc
    if issue == "NO_ISSUE":
        lakebase.log_scan(store, upc, "NO_ISSUE", issue, None, served_by, db_ms, actor)
        return {"status": "NO_ISSUE", "store": store, "upc": upc, "product": product, "event": r, **timing,
                "sst_display": {"product": product, "status": "AVAILABLE", "reason_code": None,
                                "category": r.get("category"), "supplier": r.get("supplier"),
                                "on_hand": r.get("on_hand_units")}}
    reason = r.get("consensus_reason") or "INVESTIGATE"
    qty_col, qty_label = _QTY_BY_REASON.get(reason, (None, None))
    lakebase.log_scan(store, upc, "ISSUE_FOUND", issue, reason, served_by, db_ms, actor)
    return {"status": "ISSUE_FOUND", "store": store, "upc": upc, "event": r, **timing,
            "sst_display": {"product": product, "status": issue, "low_type": r.get("low_issue"),
                            "reason_code": reason, "reason_text": nba.REASON_LABEL.get(reason, ""),
                            "category": r.get("category"), "supplier": r.get("supplier"), "depot": r.get("depot"),
                            "qty_label": qty_label, "qty": r.get(qty_col) if qty_col else None,
                            "evidence_found": r.get("evidence_found") or "",
                            "actions": [{"type": t, "label": lbl} for t, lbl in ACTION_OPTIONS.get(reason, [])]}}


@app.get("/api/sst-samples")
def api_sst_samples(store: str):
    """One representative product per distinct reason code at this store (so every reason is demoable)."""
    try:
        return {"samples": lakebase.samples(store), "served_by": "lakebase"}
    except Exception as e:
        logger.warning(f"Lakebase samples failed, using the warehouse: {e}")
    rows = execute_sql(f"""
        SELECT upc, product, issue, consensus_reason FROM (
          SELECT upc, product, issue, consensus_reason,
                 ROW_NUMBER() OVER (PARTITION BY consensus_reason ORDER BY issue, upc) AS rn
          FROM {TABLE}
          WHERE store = '{_safe_str(store)}' AND issue <> 'NO_ISSUE' AND consensus_reason IS NOT NULL
        ) WHERE rn = 1
        ORDER BY consensus_reason
    """)
    return {"samples": rows, "served_by": "warehouse"}


class SstExplainRequest(BaseModel):
    store: str
    upc: str
    event_data: dict


@app.post("/api/sst-explain")
def api_sst_explain(req: SstExplainRequest, request: Request):
    """Next best action: the playbook action for the root cause, worded for the colleague by the LLM (see nba.py)."""
    d = req.event_data or {}
    reason = d.get("consensus_reason") or "INVESTIGATE"
    t0 = time.perf_counter()
    text = nba.clean(call_llm(nba.build_messages(d, req.store)))
    used_fallback = not text
    if used_fallback:
        text = nba.fallback(d, req.store)
    ms = (time.perf_counter() - t0) * 1000
    model = "fallback-template" if used_fallback else LLM_ENDPOINT
    lakebase.log_recommendation(req.store, req.upc, reason, model, nba.PROMPT_VERSION, text, ms, _actor(request))
    return {"explanation": text, "model": model, "prompt_version": nba.PROMPT_VERSION, "latency_ms": round(ms)}


# --- Colleague actions: written to Lakebase, streamed back to Unity Catalog by Lakehouse Sync ---
class ActionRequest(BaseModel):
    store: str
    upc: str
    action_type: str
    note: Optional[str] = ""


@app.post("/api/actions")
def api_add_action(req: ActionRequest, request: Request):
    if req.action_type not in _VALID_ACTIONS:
        raise HTTPException(status_code=400, detail="Unknown action type")
    r, _ = lakebase.lookup(req.store, req.upc)          # record what the data says, not what the browser sent
    if not r:
        raise HTTPException(status_code=404, detail="Product is not ranged at this store")
    role = getattr(request.state, "user_role", None) or {}
    row = lakebase.add_action(r.get("business_date"), req.store, req.upc, r.get("product"), r.get("issue"),
                              r.get("consensus_reason"), req.action_type, (req.note or "")[:500], _actor(request),
                              role.get("persona"))
    return {"status": "ok", "action": row}


@app.get("/api/actions")
def api_list_actions(store: str):
    return {"actions": lakebase.list_actions(store)}


@app.get("/api/actions/summary")
def api_actions_summary():
    return {"summary": lakebase.action_summary()}


# --- Data journey: the end-to-end flow with live counts at every stage ---
_journey_cache: dict = {"ts": 0.0, "uc": None}


@app.get("/api/journey")
def api_journey():
    """Counts at each stage. Pipeline stages come from the daily run's checks (ops.pipeline_checks);
    Lakebase and the actions loop are counted live."""
    if not _journey_cache["uc"] or time.time() - _journey_cache["ts"] > 300:
        checks = execute_sql(f"""
            SELECT stage, metric, value, expected, passed, business_date, run_at
            FROM {CATALOG}.ops.pipeline_checks
            WHERE run_id = (SELECT max_by(run_id, run_at) FROM {CATALOG}.ops.pipeline_checks)
            ORDER BY stage_order, metric""")
        loop = execute_sql(f"""
            SELECT (SELECT COUNT(*) FROM {CATALOG}.ops.lb_colleague_actions_history WHERE _pg_change_type = 'insert') AS actions_in_uc,
                   (SELECT COUNT(*) FROM {CATALOG}.ops.lb_scan_log_history WHERE _pg_change_type = 'insert') AS scans_in_uc""")
        _journey_cache.update(ts=time.time(), uc={"checks": checks, "loop": loop[0] if loop else {}})
    live = {}
    try:
        rows, ms = lakebase.query(
            "SELECT (SELECT COUNT(*) FROM serving.product_location_status) AS serving_rows, "
            "(SELECT COUNT(*) FROM ops.colleague_actions) AS actions, (SELECT COUNT(*) FROM ops.scan_log) AS scans, "
            "(SELECT COUNT(*) FROM ops.ai_recommendations) AS recommendations")
        live = {**rows[0], "query_ms": round(ms, 1)}
    except Exception as e:
        live = {"error": str(e)[:200]}
    return {**_journey_cache["uc"], "lakebase": live}


@app.get("/api/health")
def api_health():
    return {"lakebase": lakebase.health(), "genie_space_configured": bool(GENIE_SPACE_ID),
            "warehouse_configured": bool(WAREHOUSE_ID), "llm_endpoint": LLM_ENDPOINT}


# --- Static files ---
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")
