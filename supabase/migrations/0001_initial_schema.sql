-- ══════════════════════════════════════════════════════════════════════════════
-- Sententia.ai — Initial Schema Migration
-- Version:  0001
-- Target:   Supabase (Postgres 15)
--
-- Tables:
--   1. firm_workspaces   — tenant / firm accounts
--   2. users             — authenticated users, linked to a workspace
--   3. scenarios         — deal scenario inputs (jurisdictions, amounts, docs)
--   4. structures        — generated investment structures per scenario
--   5. review_queue      — human reviewer workflow for flagged structures
--   6. audit_log         — immutable actor + timestamp trail for every action
--
-- Paste this into Supabase → SQL Editor → New query → Run
-- ══════════════════════════════════════════════════════════════════════════════

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Helpers ───────────────────────────────────────────────────────────────────
-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ════════════════════════════════════════════════════════════════════════════
-- 1. firm_workspaces
--    One row per law firm / fund / enterprise tenant.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS firm_workspaces (
  id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT        NOT NULL,
  plan          TEXT        NOT NULL DEFAULT 'free'
                            CHECK (plan IN ('free', 'pro', 'enterprise')),
  domain        TEXT,                            -- optional verified email domain
  metadata      JSONB       NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at_firm_workspaces
  BEFORE UPDATE ON firm_workspaces
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE firm_workspaces ENABLE ROW LEVEL SECURITY;


-- ════════════════════════════════════════════════════════════════════════════
-- 2. users
--    Linked to Supabase auth.users via id (same UUID).
--    role: 'analyst' | 'reviewer' | 'admin'
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
  id                  UUID        PRIMARY KEY,   -- matches auth.users.id
  email               TEXT        NOT NULL UNIQUE,
  full_name           TEXT,
  role                TEXT        NOT NULL DEFAULT 'analyst'
                                  CHECK (role IN ('analyst', 'reviewer', 'admin')),
  firm_workspace_id   UUID        REFERENCES firm_workspaces(id) ON DELETE SET NULL,
  is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
  last_login_at       TIMESTAMPTZ,
  metadata            JSONB       NOT NULL DEFAULT '{}',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_firm_workspace
  ON users(firm_workspace_id);

CREATE TRIGGER set_updated_at_users
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE users ENABLE ROW LEVEL SECURITY;


-- ════════════════════════════════════════════════════════════════════════════
-- 3. scenarios
--    One row per deal query submitted by a user.
--    Captures all inputs needed to generate structures.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS scenarios (
  id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id                 UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  firm_workspace_id       UUID        REFERENCES firm_workspaces(id) ON DELETE SET NULL,

  -- Jurisdiction inputs
  origin_jurisdiction     TEXT        NOT NULL,   -- e.g. "CHINA"
  spv_jurisdiction        TEXT,                   -- e.g. "SINGAPORE" (intermediate)
  target_jurisdiction     TEXT        NOT NULL,   -- e.g. "INDIA"

  -- Deal parameters
  investment_amount_usd   NUMERIC(18, 2),
  equity_pct              NUMERIC(5, 2),          -- 0.00–100.00
  control_rights          TEXT[],                 -- e.g. ['board_seat', 'veto_rights']

  -- Document upload (optional)
  uploaded_doc_url        TEXT,                   -- Supabase Storage URL
  parsed_doc_json         JSONB,                  -- Docling extraction output

  -- Free-text notes from the analyst
  notes                   TEXT,

  status                  TEXT        NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft', 'processing', 'completed', 'failed')),

  metadata                JSONB       NOT NULL DEFAULT '{}',
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenarios_user_id
  ON scenarios(user_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_workspace
  ON scenarios(firm_workspace_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_status
  ON scenarios(status);

CREATE TRIGGER set_updated_at_scenarios
  BEFORE UPDATE ON scenarios
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;


-- ════════════════════════════════════════════════════════════════════════════
-- 4. structures
--    Generated investment structure proposals — 2–4 per scenario.
--    execution_layer tells the UI whether OPA or LLM produced this.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS structures (
  id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  scenario_id         UUID        NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,

  -- Structure metadata
  structure_label     TEXT        NOT NULL,   -- e.g. "Primary Structure", "Alternative A"
  structure_type      TEXT,                   -- e.g. "SPV_LAYERED", "DIRECT_FDI"
  layering_json       JSONB       NOT NULL DEFAULT '{}',
  -- ^ Structured representation: entities, ownership %, jurisdiction, roles

  -- Human-readable output
  rationale           TEXT,                   -- "Why this structure" narrative
  mermaid_diagram     TEXT,                   -- Mermaid graph TD string for the diagram

  -- Compliance metadata
  execution_layer     TEXT        NOT NULL
                      CHECK (execution_layer IN ('DETERMINISTIC_RULE_ENGINE', 'LLM_FALLBACK_REASONING')),
  is_rule_validated   BOOLEAN     NOT NULL DEFAULT FALSE,
  compliance_flags    JSONB       NOT NULL DEFAULT '[]',
  -- ^ Array of {rule_id, description, status: 'pass'|'fail'|'warn'}

  ui_banner           JSONB,
  -- ^ { type: 'WARNING', label: '...', message: '...' } or null

  -- LLM metadata (for debugging / audit)
  llm_model_used      TEXT,
  llm_tokens_used     INTEGER,

  status              TEXT        NOT NULL DEFAULT 'generated'
                      CHECK (status IN ('generated', 'under_review', 'approved', 'flagged', 'archived')),

  metadata            JSONB       NOT NULL DEFAULT '{}',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_structures_scenario_id
  ON structures(scenario_id);
CREATE INDEX IF NOT EXISTS idx_structures_execution_layer
  ON structures(execution_layer);
CREATE INDEX IF NOT EXISTS idx_structures_status
  ON structures(status);

CREATE TRIGGER set_updated_at_structures
  BEFORE UPDATE ON structures
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE structures ENABLE ROW LEVEL SECURITY;


-- ════════════════════════════════════════════════════════════════════════════
-- 5. review_queue
--    Human reviewer workflow — one row per review task.
--    Matches PRD Section 8.6 (reviewer gating before structures are surfaced).
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS review_queue (
  id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  structure_id    UUID        NOT NULL REFERENCES structures(id) ON DELETE CASCADE,
  reviewer_id     UUID        REFERENCES users(id) ON DELETE SET NULL,

  status          TEXT        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'in_review', 'approved', 'flagged', 'escalated')),

  -- Reviewer notes and decision rationale
  notes           TEXT,
  flag_reason     TEXT,       -- populated when status = 'flagged'

  -- SLA tracking
  assigned_at     TIMESTAMPTZ,
  reviewed_at     TIMESTAMPTZ,
  due_at          TIMESTAMPTZ,

  metadata        JSONB       NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_queue_structure_id
  ON review_queue(structure_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_reviewer_id
  ON review_queue(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_status
  ON review_queue(status);

CREATE TRIGGER set_updated_at_review_queue
  BEFORE UPDATE ON review_queue
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE review_queue ENABLE ROW LEVEL SECURITY;


-- ════════════════════════════════════════════════════════════════════════════
-- 6. audit_log
--    Immutable append-only trail — actor + action + entity + timestamp.
--    Matches PRD Section 8.7 (full audit trail).
--    NOTE: Do NOT add UPDATE/DELETE triggers on this table.
--          Rows must never be modified after insert.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_log (
  id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Who did it
  actor_id      UUID        REFERENCES users(id) ON DELETE SET NULL,
  actor_email   TEXT,       -- denormalized — preserved even if user is deleted

  -- What happened
  action        TEXT        NOT NULL,
  -- e.g. 'scenario.created', 'structure.generated', 'review.approved', 'user.login'

  -- On what
  entity_type   TEXT,       -- 'scenario' | 'structure' | 'review_queue' | 'user' etc.
  entity_id     UUID,       -- FK to the affected row (soft reference — no FK constraint)

  -- Context
  metadata      JSONB       NOT NULL DEFAULT '{}',
  -- ^ Arbitrary context: IP address, user-agent, diff, etc.

  ip_address    INET,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
  -- No updated_at — this table is append-only
);

CREATE INDEX IF NOT EXISTS idx_audit_log_actor_id
  ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity
  ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at
  ON audit_log(created_at DESC);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Prevent any UPDATE or DELETE on audit_log (immutability enforcement)
CREATE OR REPLACE RULE no_update_audit_log AS
  ON UPDATE TO audit_log DO INSTEAD NOTHING;

CREATE OR REPLACE RULE no_delete_audit_log AS
  ON DELETE TO audit_log DO INSTEAD NOTHING;


-- ══════════════════════════════════════════════════════════════════════════════
-- Done.
-- Tables created: firm_workspaces, users, scenarios, structures,
--                 review_queue, audit_log
-- RLS enabled on all tables. Add policies based on your auth strategy.
-- ══════════════════════════════════════════════════════════════════════════════
