-- Lakebase (Postgres) operational tables, written by the Shelf Availability app.
-- Lakehouse Sync streams every insert and update to Unity Catalog (larkwell_osa.ops.lb_<table>_history),
-- which is how actions taken in stores flow back into the lakehouse for Genie and reporting.
-- Larkwell Foods is fictitious; all data is synthetic.

CREATE SCHEMA IF NOT EXISTS ops;

-- What a colleague did about a gap or low: the operational record that closes the loop.
CREATE TABLE IF NOT EXISTS ops.colleague_actions (
  action_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  business_date DATE NOT NULL,
  store         TEXT NOT NULL,
  upc           TEXT NOT NULL,
  product       TEXT,
  issue         TEXT,
  root_cause    TEXT,
  action_type   TEXT NOT NULL,
  note          TEXT,
  status        TEXT NOT NULL DEFAULT 'OPEN',
  actor_email   TEXT NOT NULL,
  persona       TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS colleague_actions_store_idx ON ops.colleague_actions (store, created_at DESC);

-- Every Shelf Scan lookup: adoption and latency telemetry.
CREATE TABLE IF NOT EXISTS ops.scan_log (
  scan_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  scanned_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  store       TEXT NOT NULL,
  upc         TEXT NOT NULL,
  status      TEXT,
  issue       TEXT,
  root_cause  TEXT,
  served_by   TEXT,
  lookup_ms   NUMERIC(10, 1),
  actor_email TEXT
);

-- Every next-best-action the AI wrote, kept for review and evaluation.
CREATE TABLE IF NOT EXISTS ops.ai_recommendations (
  rec_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  store          TEXT NOT NULL,
  upc            TEXT NOT NULL,
  root_cause     TEXT,
  model          TEXT,
  prompt_version TEXT,
  recommendation TEXT,
  latency_ms     NUMERIC(10, 1),
  actor_email    TEXT
);

-- Thumbs up or down on Genie answers.
CREATE TABLE IF NOT EXISTS ops.genie_feedback (
  feedback_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  message_id      TEXT,
  conversation_id TEXT,
  is_positive     BOOLEAN,
  comment         TEXT,
  question        TEXT,
  answer          TEXT,
  sql_generated   TEXT,
  actor_email     TEXT
);

-- Lakehouse Sync needs full row images to capture updates and deletes.
ALTER TABLE ops.colleague_actions REPLICA IDENTITY FULL;
ALTER TABLE ops.scan_log REPLICA IDENTITY FULL;
ALTER TABLE ops.ai_recommendations REPLICA IDENTITY FULL;
ALTER TABLE ops.genie_feedback REPLICA IDENTITY FULL;
