-- ══════════════════════════════════════════════════════════════════════════════
-- Sententia.ai — Complete Master Setup Migration
-- Version:  0000_master_setup
-- Target:   Supabase (Postgres 15)
--
-- This single script sets up all tables, indexes, triggers, RLS policies,
-- and Auth integrations in one clean execution.
-- ══════════════════════════════════════════════════════════════════════════════

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Helpers ───────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ════════════════════════════════════════════════════════════════════════════
-- 1. firm_workspaces
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS firm_workspaces (
  id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT        NOT NULL,
  plan          TEXT        NOT NULL DEFAULT 'free'
                            CHECK (plan IN ('free', 'pro', 'enterprise')),
  domain        TEXT,
  metadata      JSONB       NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS set_updated_at_firm_workspaces ON firm_workspaces;
CREATE TRIGGER set_updated_at_firm_workspaces
  BEFORE UPDATE ON firm_workspaces
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE firm_workspaces ENABLE ROW LEVEL SECURITY;

-- ════════════════════════════════════════════════════════════════════════════
-- 2. users
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
  id                  UUID        PRIMARY KEY,   -- matches auth.users.id
  email               TEXT        NOT NULL UNIQUE,
  full_name           TEXT,
  role                TEXT        NOT NULL DEFAULT 'associate'
                                  CHECK (role IN ('associate', 'reviewer', 'compliance_officer', 'admin')),
  firm_workspace_id   UUID        REFERENCES firm_workspaces(id) ON DELETE SET NULL,
  is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
  last_login_at       TIMESTAMPTZ,
  metadata            JSONB       NOT NULL DEFAULT '{}',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_firm_workspace ON users(firm_workspace_id);

DROP TRIGGER IF EXISTS set_updated_at_users ON users;
CREATE TRIGGER set_updated_at_users
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- ════════════════════════════════════════════════════════════════════════════
-- 3. scenarios
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS scenarios (
  id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id                 UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  firm_workspace_id       UUID        REFERENCES firm_workspaces(id) ON DELETE SET NULL,
  origin_jurisdiction     TEXT        NOT NULL,
  spv_jurisdiction        TEXT,
  target_jurisdiction     TEXT        NOT NULL,
  investment_amount_usd   NUMERIC(18, 2),
  equity_pct              NUMERIC(5, 2),
  control_rights          TEXT[],
  uploaded_doc_url        TEXT,
  parsed_doc_json         JSONB,
  notes                   TEXT,
  status                  TEXT        NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft', 'processing', 'completed', 'failed')),
  metadata                JSONB       NOT NULL DEFAULT '{}',
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenarios_user_id ON scenarios(user_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_workspace ON scenarios(firm_workspace_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_status ON scenarios(status);

DROP TRIGGER IF EXISTS set_updated_at_scenarios ON scenarios;
CREATE TRIGGER set_updated_at_scenarios
  BEFORE UPDATE ON scenarios
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;

-- ════════════════════════════════════════════════════════════════════════════
-- 4. structures
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS structures (
  id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  scenario_id         UUID        NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
  structure_label     TEXT        NOT NULL,
  structure_type      TEXT,
  layering_json       JSONB       NOT NULL DEFAULT '{}',
  rationale           TEXT,
  mermaid_diagram     TEXT,
  execution_layer     TEXT        NOT NULL
                      CHECK (execution_layer IN ('DETERMINISTIC_RULE_ENGINE', 'LLM_FALLBACK_REASONING')),
  is_rule_validated   BOOLEAN     NOT NULL DEFAULT FALSE,
  compliance_flags    JSONB       NOT NULL DEFAULT '[]',
  ui_banner           JSONB,
  llm_model_used      TEXT,
  llm_tokens_used     INTEGER,
  status              TEXT        NOT NULL DEFAULT 'generated'
                      CHECK (status IN ('generated', 'under_review', 'approved', 'flagged', 'archived')),
  metadata            JSONB       NOT NULL DEFAULT '{}',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_structures_scenario_id ON structures(scenario_id);
CREATE INDEX IF NOT EXISTS idx_structures_execution_layer ON structures(execution_layer);
CREATE INDEX IF NOT EXISTS idx_structures_status ON structures(status);

DROP TRIGGER IF EXISTS set_updated_at_structures ON structures;
CREATE TRIGGER set_updated_at_structures
  BEFORE UPDATE ON structures
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE structures ENABLE ROW LEVEL SECURITY;

-- ════════════════════════════════════════════════════════════════════════════
-- 5. review_queue
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS review_queue (
  id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  structure_id    UUID        NOT NULL REFERENCES structures(id) ON DELETE CASCADE,
  reviewer_id     UUID        REFERENCES users(id) ON DELETE SET NULL,
  status          TEXT        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'in_review', 'approved', 'flagged', 'escalated')),
  notes           TEXT,
  flag_reason     TEXT,
  assigned_at     TIMESTAMPTZ,
  reviewed_at     TIMESTAMPTZ,
  due_at          TIMESTAMPTZ,
  metadata        JSONB       NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_queue_structure_id ON review_queue(structure_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_reviewer_id ON review_queue(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);

DROP TRIGGER IF EXISTS set_updated_at_review_queue ON review_queue;
CREATE TRIGGER set_updated_at_review_queue
  BEFORE UPDATE ON review_queue
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE review_queue ENABLE ROW LEVEL SECURITY;

-- ════════════════════════════════════════════════════════════════════════════
-- 6. reviewer_corrections
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS reviewer_corrections (
  id                UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  review_queue_id   UUID        REFERENCES review_queue(id) ON DELETE CASCADE,
  structure_id      UUID        REFERENCES structures(id)   ON DELETE CASCADE,
  reviewer_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  firm_workspace_id UUID        REFERENCES firm_workspaces(id) ON DELETE SET NULL,
  correction_type   TEXT        NOT NULL
                    CHECK (correction_type IN (
                      'jurisdiction_error', 'ownership_threshold', 'regulatory_gap',
                      'tax_issue', 'structure_type_wrong', 'risk_severity_wrong',
                      'missing_touchpoint', 'citation_error', 'treaty_benefit_wrong',
                      'gaar_issue', 'other'
                    )),
  affected_field    TEXT        NOT NULL,
  original_value    TEXT,
  corrected_value   TEXT        NOT NULL,
  jurisdiction      TEXT,
  severity          TEXT        NOT NULL DEFAULT 'medium'
                    CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  notes             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviewer_corrections_review_queue ON reviewer_corrections(review_queue_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_corrections_structure ON reviewer_corrections(structure_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_corrections_reviewer ON reviewer_corrections(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_corrections_type ON reviewer_corrections(correction_type);

ALTER TABLE reviewer_corrections ENABLE ROW LEVEL SECURITY;

-- ════════════════════════════════════════════════════════════════════════════
-- 7. audit_log
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_log (
  id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor_id            UUID        REFERENCES users(id) ON DELETE SET NULL,
  actor_email         TEXT,
  firm_workspace_id   UUID        REFERENCES firm_workspaces(id) ON DELETE SET NULL,
  action              TEXT        NOT NULL DEFAULT 'compliance_check',
  action_category     TEXT        CHECK (action_category IN ('auth', 'scenario', 'structure', 'compliance', 'diagram', 'review', 'export', 'admin')),
  entity_type         TEXT,
  entity_id           UUID,
  corridor_id         TEXT,
  policy_package      TEXT,
  evaluation_mode     TEXT,
  scenario_id         UUID        REFERENCES scenarios(id) ON DELETE SET NULL,
  structure_rank      INTEGER,
  input_data          JSONB       NOT NULL DEFAULT '{}'::jsonb,
  violations          JSONB       NOT NULL DEFAULT '[]'::jsonb,
  warnings            JSONB       NOT NULL DEFAULT '[]'::jsonb,
  required_approvals  JSONB       NOT NULL DEFAULT '[]'::jsonb,
  is_allowed          BOOLEAN     NOT NULL DEFAULT TRUE,
  is_rule_validated   BOOLEAN     NOT NULL DEFAULT TRUE,
  blocking_count      INTEGER     NOT NULL DEFAULT 0,
  warning_count       INTEGER     NOT NULL DEFAULT 0,
  metadata            JSONB       NOT NULL DEFAULT '{}'::jsonb,
  ip_address          INET
);

CREATE INDEX IF NOT EXISTS idx_audit_log_scenario_id ON audit_log(scenario_id) WHERE scenario_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_log_corridor_id ON audit_log(corridor_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_workspace ON audit_log(firm_workspace_id, created_at DESC);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- ════════════════════════════════════════════════════════════════════════════
-- 8. RLS Functions & Workspace Scoped Policies
-- ════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION auth_user_workspace_id() RETURNS UUID AS $$
  SELECT firm_workspace_id FROM users WHERE id = auth.uid()
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION auth_user_role() RETURNS TEXT AS $$
  SELECT role FROM users WHERE id = auth.uid()
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- firm_workspaces RLS
DROP POLICY IF EXISTS "workspace_self" ON firm_workspaces;
CREATE POLICY "workspace_self" ON firm_workspaces FOR SELECT USING (id = auth_user_workspace_id());
DROP POLICY IF EXISTS "workspace_admin_update" ON firm_workspaces;
CREATE POLICY "workspace_admin_update" ON firm_workspaces FOR UPDATE USING (id = auth_user_workspace_id() AND auth_user_role() = 'admin');

-- users RLS
DROP POLICY IF EXISTS "users_own_profile" ON users;
CREATE POLICY "users_own_profile" ON users FOR ALL USING (id = auth.uid());
DROP POLICY IF EXISTS "admin_workspace_users" ON users;
CREATE POLICY "admin_workspace_users" ON users FOR SELECT USING (firm_workspace_id = auth_user_workspace_id() AND auth_user_role() IN ('admin', 'compliance_officer'));

-- scenarios RLS
DROP POLICY IF EXISTS "scenarios_workspace_read" ON scenarios;
CREATE POLICY "scenarios_workspace_read" ON scenarios FOR SELECT USING (firm_workspace_id = auth_user_workspace_id());
DROP POLICY IF EXISTS "scenarios_create" ON scenarios;
CREATE POLICY "scenarios_create" ON scenarios FOR INSERT WITH CHECK (firm_workspace_id = auth_user_workspace_id() AND auth.uid() = user_id);
DROP POLICY IF EXISTS "scenarios_update" ON scenarios;
CREATE POLICY "scenarios_update" ON scenarios FOR UPDATE USING (firm_workspace_id = auth_user_workspace_id() AND (user_id = auth.uid() OR auth_user_role() = 'admin'));

-- structures RLS
DROP POLICY IF EXISTS "structures_workspace_read" ON structures;
CREATE POLICY "structures_workspace_read" ON structures FOR SELECT USING (EXISTS (SELECT 1 FROM scenarios s WHERE s.id = structures.scenario_id AND s.firm_workspace_id = auth_user_workspace_id()));

-- review_queue RLS
DROP POLICY IF EXISTS "review_queue_workspace_read" ON review_queue;
CREATE POLICY "review_queue_workspace_read" ON review_queue FOR SELECT USING (EXISTS (SELECT 1 FROM structures st JOIN scenarios sc ON sc.id = st.scenario_id WHERE st.id = review_queue.structure_id AND sc.firm_workspace_id = auth_user_workspace_id()));
DROP POLICY IF EXISTS "review_queue_reviewer_update" ON review_queue;
CREATE POLICY "review_queue_reviewer_update" ON review_queue FOR UPDATE USING (auth_user_role() IN ('reviewer', 'compliance_officer', 'admin') AND EXISTS (SELECT 1 FROM structures st JOIN scenarios sc ON sc.id = st.scenario_id WHERE st.id = review_queue.structure_id AND sc.firm_workspace_id = auth_user_workspace_id()));

-- reviewer_corrections RLS
DROP POLICY IF EXISTS "corrections_workspace_read" ON reviewer_corrections;
CREATE POLICY "corrections_workspace_read" ON reviewer_corrections FOR SELECT USING (firm_workspace_id = auth_user_workspace_id());
DROP POLICY IF EXISTS "corrections_reviewer_insert" ON reviewer_corrections;
CREATE POLICY "corrections_reviewer_insert" ON reviewer_corrections FOR INSERT WITH CHECK (firm_workspace_id = auth_user_workspace_id() AND reviewer_id = auth.uid() AND auth_user_role() IN ('reviewer', 'compliance_officer', 'admin'));

-- audit_log RLS
DROP POLICY IF EXISTS "audit_log_workspace_read" ON audit_log;
CREATE POLICY "audit_log_workspace_read" ON audit_log FOR SELECT USING (firm_workspace_id = auth_user_workspace_id() AND auth_user_role() IN ('compliance_officer', 'admin'));

-- ════════════════════════════════════════════════════════════════════════════
-- 9. Triggers
-- ════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION auto_enqueue_structure_review()
RETURNS TRIGGER AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM review_queue WHERE structure_id = NEW.id) THEN
    INSERT INTO review_queue (structure_id, status, created_at, updated_at)
    VALUES (NEW.id, 'pending', NOW(), NOW());
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_auto_enqueue_structure ON structures;
CREATE TRIGGER trg_auto_enqueue_structure
  AFTER INSERT ON structures
  FOR EACH ROW EXECUTE FUNCTION auto_enqueue_structure_review();

CREATE OR REPLACE FUNCTION sync_structure_status_from_review()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'approved' THEN
    UPDATE structures SET status = 'approved', updated_at = NOW() WHERE id = NEW.structure_id;
  ELSIF NEW.status = 'flagged' THEN
    UPDATE structures SET status = 'flagged', updated_at = NOW() WHERE id = NEW.structure_id;
  ELSIF NEW.status = 'in_review' THEN
    UPDATE structures SET status = 'under_review', updated_at = NOW() WHERE id = NEW.structure_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_sync_structure_status ON review_queue;
CREATE TRIGGER trg_sync_structure_status
  AFTER UPDATE OF status ON review_queue
  FOR EACH ROW EXECUTE FUNCTION sync_structure_status_from_review();

CREATE OR REPLACE FUNCTION handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, role, is_active, created_at)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    'associate',
    TRUE,
    NOW()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_auth_user();
