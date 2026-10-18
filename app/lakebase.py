"""Lakebase (Postgres) access for the Shelf Availability app.

Reads: Shelf Scan looks up one product-location at a time in serving.product_location_status, the gold table that
Unity Catalog keeps in sync with Lakebase. That's a point lookup on the primary key (store, upc), which Postgres
answers in milliseconds.

Writes: colleague actions, scan telemetry, AI recommendations and Genie feedback go to the ops schema.
Lakehouse Sync streams every change to Unity Catalog (larkwell_osa.ops.lb_<table>_history), so what happens in
stores flows back into the lakehouse for Genie and reporting.

Connections authenticate as the app's service principal with short-lived OAuth credentials, pooled and refreshed
before they expire.
"""
import logging
import os
import queue
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

ENDPOINT = os.getenv("LAKEBASE_ENDPOINT", "projects/larkwell-osa/branches/production/endpoints/primary")
DATABASE = os.getenv("LAKEBASE_DATABASE", "databricks_postgres")
POOL_SIZE = int(os.getenv("LAKEBASE_POOL_SIZE", "8"))
CREDENTIAL_TTL_S = 40 * 60      # OAuth credentials last an hour; renew well before that
CONNECTION_MAX_AGE_S = 50 * 60

# Columns the app reads for a Shelf Scan (same shape as the warehouse query it replaces).
SCAN_COLUMNS = ("store, upc, product, category, super_group, product_group, issue, low_issue, consensus_reason, "
                "consensus_reason_retail, supplier, depot, known_gap, supplier_short, supplier_short_type, scarcity, "
                "waste, under_forecast, order_delivery_block, upstream_issue, supplier_short_qty, scarcity_qty, "
                "waste_qty, under_forecast_qty, under_space_qty, stockfile_adjustment_qty, on_hand_units, "
                "presentation_min_units, forecast_units, days_of_cover, evidence_found, business_date")


class _Pool:
    """A small thread-safe pool. Connections are recycled before their credential would need renewing."""

    def __init__(self):
        self._idle = queue.LifoQueue(maxsize=POOL_SIZE)
        self._lock = threading.Lock()
        self._cred = {"host": None, "user": None, "token": None, "issued": 0.0}

    def _credentials(self):
        with self._lock:
            if self._cred["token"] and time.time() - self._cred["issued"] < CREDENTIAL_TTL_S:
                return self._cred
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            host = self._cred["host"] or w.postgres.get_endpoint(ENDPOINT).status.hosts.host
            user = os.getenv("DATABRICKS_CLIENT_ID") or w.current_user.me().user_name
            token = w.postgres.generate_database_credential(ENDPOINT).token
            self._cred = {"host": host, "user": user, "token": token, "issued": time.time()}
            logger.info("Lakebase: new credential for %s on %s", user, host)
            return self._cred

    def _connect(self):
        c = self._credentials()
        conn = psycopg2.connect(host=c["host"], port=5432, dbname=DATABASE, user=c["user"], password=c["token"],
                                sslmode="require", connect_timeout=5, application_name="larkwell-shelf-availability")
        conn.autocommit = True
        return conn, time.time()

    @contextmanager
    def connection(self):
        conn, opened_at = None, 0.0
        try:
            conn, opened_at = self._idle.get_nowait()
            if conn.closed or time.time() - opened_at > CONNECTION_MAX_AGE_S:
                conn.close()
                conn = None
        except queue.Empty:
            pass
        if conn is None:
            conn, opened_at = self._connect()
        healthy = True
        try:
            yield conn
        except Exception:
            healthy = False
            raise
        finally:
            if healthy and not conn.closed:
                try:
                    self._idle.put_nowait((conn, opened_at))
                except queue.Full:
                    conn.close()
            else:
                try:
                    conn.close()
                except Exception:
                    pass


_pool = _Pool()


def _text(v):
    """Match the SQL Statement API's wire format (everything a string) so the frontend sees one shape."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (float, Decimal)):
        return str(float(v))
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return str(v) if not isinstance(v, str) else v


def query(sql, params=(), as_text=True):
    """Run a read query. Returns (rows as dicts, milliseconds)."""
    t0 = time.perf_counter()
    with _pool.connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    ms = (time.perf_counter() - t0) * 1000
    if as_text:
        rows = [{k: _text(v) for k, v in r.items()} for r in rows]
    return [dict(r) for r in rows], ms


def execute(sql, params=()):
    """Run a write. Returns the RETURNING row (if any) as a dict."""
    with _pool.connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        try:
            row = cur.fetchone()
        except psycopg2.ProgrammingError:
            row = None
    return {k: _text(v) for k, v in row.items()} if row else None


def fire_and_forget(sql, params=()):
    """Telemetry writes must never slow a colleague down."""
    def _run():
        try:
            execute(sql, params)
        except Exception as e:  # noqa: BLE001
            logger.warning("Lakebase write failed (non-fatal): %s", e)
    threading.Thread(target=_run, daemon=True).start()


# --- Shelf Scan -----------------------------------------------------------------------------------------------

def lookup(store, upc):
    rows, ms = query(f"SELECT {SCAN_COLUMNS} FROM serving.product_location_status WHERE store = %s AND upc = %s",
                     (store, upc))
    return (rows[0] if rows else None), ms


def samples(store):
    rows, _ = query(
        "SELECT DISTINCT ON (consensus_reason) upc, product, issue, consensus_reason "
        "FROM serving.product_location_status "
        "WHERE store = %s AND issue <> 'NO_ISSUE' AND consensus_reason IS NOT NULL "
        "ORDER BY consensus_reason, issue, upc", (store,))
    return rows


def log_scan(store, upc, status, issue, root_cause, served_by, lookup_ms, actor):
    fire_and_forget(
        "INSERT INTO ops.scan_log (store, upc, status, issue, root_cause, served_by, lookup_ms, actor_email) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (store, upc, status, issue, root_cause, served_by, round(lookup_ms, 1), actor))


# --- Colleague actions (closing the loop) ---------------------------------------------------------------------

def add_action(business_date, store, upc, product, issue, root_cause, action_type, note, actor, persona):
    return execute(
        "INSERT INTO ops.colleague_actions (business_date, store, upc, product, issue, root_cause, action_type, note, "
        "actor_email, persona) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "RETURNING action_id, created_at, status",
        (business_date, store, upc, product, issue, root_cause, action_type, note, actor, persona))


def list_actions(store, limit=8):
    rows, _ = query(
        "SELECT action_id, created_at, product, upc, root_cause, action_type, note, status, actor_email "
        "FROM ops.colleague_actions WHERE store = %s ORDER BY created_at DESC LIMIT %s", (store, limit))
    return rows


def action_summary():
    rows, _ = query(
        "SELECT action_type, COUNT(*) AS actions, COUNT(DISTINCT store) AS stores "
        "FROM ops.colleague_actions WHERE created_at >= now() - interval '1 day' GROUP BY action_type ORDER BY 2 DESC")
    return rows


# --- AI and Genie telemetry -----------------------------------------------------------------------------------

def log_recommendation(store, upc, root_cause, model, prompt_version, text, latency_ms, actor):
    fire_and_forget(
        "INSERT INTO ops.ai_recommendations (store, upc, root_cause, model, prompt_version, recommendation, latency_ms, "
        "actor_email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (store, upc, root_cause, model, prompt_version, text, round(latency_ms, 1), actor))


def log_feedback(message_id, conversation_id, is_positive, comment, question, answer, sql, actor):
    fire_and_forget(
        "INSERT INTO ops.genie_feedback (message_id, conversation_id, is_positive, comment, question, answer, "
        "sql_generated, actor_email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (message_id, conversation_id, is_positive, comment, question, answer, sql, actor))


def health():
    t0 = time.perf_counter()
    try:
        rows, _ = query("SELECT COUNT(*) AS n FROM ops.colleague_actions")
        return {"ok": True, "ms": round((time.perf_counter() - t0) * 1000, 1), "actions_logged": int(rows[0]["n"])}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}
