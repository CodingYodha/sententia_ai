-- ══════════════════════════════════════════════════════════════════════════════
-- Sententia.ai — Auth, RBAC, RLS & Human-in-Loop Migration
-- Version:  0003
-- Target:   Supabase (Postgres 15)
--
-- This migration:
--   1. Aligns 'users' role enum with PRD FR-7.1 (4 roles)
--   2. Adds 'reviewer_corrections' table (FR-6.3 — structured, not free text)
--   3. Adds workspace-scoped RLS policies to all tables
--   4. Adds audit_log firm_workspace_id + action-type columns
--   5. Adds auto-enqueue trigger: new structure → review_queue 'pending'
--   6. Enables Supabase Auth Google OAuth scaffolding comments
--
-- Run in Supabase → SQL Editor → New query → Run
-- ══════════════════════════════════════════════════════════════════════════════

-- ── 1. Align role enum to PRD FR-7.1 ─────────────────────────────────────────
-- PRD defines: associate, partner/reviewer, compliance_officer, admin
-- Existing: analyst, reviewer, admin
-- We add 'associate' and 'compliance_officer', keep 'reviewer' for backward compat

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users
  ADD CONSTRAINT users_role_check
  CHECK (role IN ('associate', 'reviewer', 'compliance_officer', 'admin'));

-- Migrate existing 'analyst' rows to 'associate'
UPDATE users SET role = 'associate' WHERE role = 'analyst';

-- ── 2. reviewer_corrections table (FR-6.3 — structured correction form) ───────
-- This captures structured corrections from reviewers so they can later feed
-- model / rule refinement — NOT free text.
CREATE TABLE IF NOT EXISTS reviewer_corrections (
  id                UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Foreign keys
  review_queue_id   UUID        REFERENCES review_queue(id) ON DELETE CASCADE,
  structure_id      UUID        REFERENCES structures(id)   ON DELETE CASCADE,
  reviewer_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  firm_workspace_id UUID        REFERENCES firm_workspaces(id) ON DELETE SET NULL,

  -- Structured correction type (FR-6.3: typed enum, not free text)
  correction_type   TEXT        NOT NULL
                    CHECK (correction_type IN (
                      'jurisdiction_error',       -- Wrong jurisdiction recommended
                      'ownership_threshold',      -- Threshold % is wrong
                      'regulatory_gap',           -- Missing regulatory requirement
                      'tax_issue',                -- Tax treatment incorrect
                      'structure_type_wrong',     -- SPV/Direct/JV choice wrong
                      'risk_severity_wrong',      -- Risk severity misjudged
                      'missing_touchpoint',       -- Compliance touchpoint omitted
                      'citation_error',           -- Source citation is wrong/hallucinated
                      'treaty_benefit_wrong',     -- Treaty benefit analysis incorrect
                      'gaar_issue',               -- GAAR/anti-avoidance flag missed
                      'other'                     -- Catch-all (requires notes)
                    )),

  -- What field is wrong
  affected_field    TEXT        NOT NULL,   -- e.g. 'ownership_chain', 'compliance_touchpoints[0].requirement'

  -- The LLM's value vs the correct value
  original_value    TEXT,                   -- What the LLM output said
  corrected_value   TEXT        NOT NULL,   -- What it should be

  -- Jurisdiction scope of the correction
  jurisdiction      TEXT,                   -- Which jurisdiction does this correction apply to

  -- Severity of the correction
  severity          TEXT        NOT NULL DEFAULT 'medium'
                    CHECK (severity IN ('low', 'medium', 'high', 'critical')),

  -- Optional explanatory note (secondary, not primary data)
  notes             TEXT,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviewer_corrections_review_queue
  ON reviewer_corrections(review_queue_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_corrections_structure
  ON reviewer_corrections(structure_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_corrections_reviewer
  ON reviewer_corrections(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_corrections_type
  ON reviewer_corrections(correction_type);

ALTER TABLE reviewer_corrections ENABLE ROW LEVEL SECURITY;

-- ── 3. Add firm_workspace_id to audit_log (for workspace-scoped audit reads) ──
ALTER TABLE audit_log
  ADD COLUMN IF NOT EXISTS firm_workspace_id UUID REFERENCES firm_workspaces(id) ON DELETE SET NULL;
ALTER TABLE audit_log
  ADD COLUMN IF NOT EXISTS action_category TEXT
  CHECK (action_category IN (
    'auth', 'scenario', 'structure', 'compliance', 'diagram', 'review', 'export', 'admin'
  ));

CREATE INDEX IF NOT EXISTS idx_audit_log_workspace
  ON audit_log(firm_workspace_id, created_at DESC);

-- ── 4. RLS Policies ───────────────────────────────────────────────────────────

-- Helper function: get the firm_workspace_id of the current auth user
CREATE OR REPLACE FUNCTION auth_user_workspace_id() RETURNS UUID AS $$
  SELECT firm_workspace_id FROM users WHERE id = auth.uid()
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Helper function: get the role of the current auth user
CREATE OR REPLACE FUNCTION auth_user_role() RETURNS TEXT AS $$
  SELECT role FROM users WHERE id = auth.uid()
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- ── 4a. firm_workspaces ───────────────────────────────────────────────────────
-- Users can only see their own workspace
DROP POLICY IF EXISTS "workspace_self" ON firm_workspaces;
CREATE POLICY "workspace_self" ON firm_workspaces
  FOR SELECT USING (id = auth_user_workspace_id());

-- Only admins can update their workspace
DROP POLICY IF EXISTS "workspace_admin_update" ON firm_workspaces;
CREATE POLICY "workspace_admin_update" ON firm_workspaces
  FOR UPDATE USING (
    id = auth_user_workspace_id()
    AND auth_user_role() = 'admin'
  );

-- ── 4b. users ─────────────────────────────────────────────────────────────────
-- Users can always read their own profile
DROP POLICY IF EXISTS "users_own_profile" ON users;
CREATE POLICY "users_own_profile" ON users
  FOR ALL USING (id = auth.uid());

-- Admins can read all users in their workspace
DROP POLICY IF EXISTS "admin_workspace_users" ON users;
CREATE POLICY "admin_workspace_users" ON users
  FOR SELECT USING (
    firm_workspace_id = auth_user_workspace_id()
    AND auth_user_role() IN ('admin', 'compliance_officer')
  );

-- ── 4c. scenarios ─────────────────────────────────────────────────────────────
-- All workspace members can read scenarios (FR-7.2: firm-level scoping)
DROP POLICY IF EXISTS "scenarios_workspace_read" ON scenarios;
CREATE POLICY "scenarios_workspace_read" ON scenarios
  FOR SELECT USING (firm_workspace_id = auth_user_workspace_id());

-- Associates and above can create scenarios
DROP POLICY IF EXISTS "scenarios_create" ON scenarios;
CREATE POLICY "scenarios_create" ON scenarios
  FOR INSERT WITH CHECK (
    firm_workspace_id = auth_user_workspace_id()
    AND auth.uid() = user_id
  );

-- Only owner or admin can update
DROP POLICY IF EXISTS "scenarios_update" ON scenarios;
CREATE POLICY "scenarios_update" ON scenarios
  FOR UPDATE USING (
    firm_workspace_id = auth_user_workspace_id()
    AND (user_id = auth.uid() OR auth_user_role() = 'admin')
  );

-- ── 4d. structures ────────────────────────────────────────────────────────────
-- All workspace members can see structures in their workspace
DROP POLICY IF EXISTS "structures_workspace_read" ON structures;
CREATE POLICY "structures_workspace_read" ON structures
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM scenarios s
      WHERE s.id = structures.scenario_id
      AND s.firm_workspace_id = auth_user_workspace_id()
    )
  );

-- ── 4e. review_queue ─────────────────────────────────────────────────────────
-- All workspace members can READ review queue (to see what's pending)
DROP POLICY IF EXISTS "review_queue_workspace_read" ON review_queue;
CREATE POLICY "review_queue_workspace_read" ON review_queue
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM structures st
      JOIN scenarios sc ON sc.id = st.scenario_id
      WHERE st.id = review_queue.structure_id
      AND sc.firm_workspace_id = auth_user_workspace_id()
    )
  );

-- Only reviewer, compliance_officer, admin can UPDATE review_queue status
DROP POLICY IF EXISTS "review_queue_reviewer_update" ON review_queue;
CREATE POLICY "review_queue_reviewer_update" ON review_queue
  FOR UPDATE USING (
    auth_user_role() IN ('reviewer', 'compliance_officer', 'admin')
    AND EXISTS (
      SELECT 1 FROM structures st
      JOIN scenarios sc ON sc.id = st.scenario_id
      WHERE st.id = review_queue.structure_id
      AND sc.firm_workspace_id = auth_user_workspace_id()
    )
  );

-- ── 4f. reviewer_corrections ──────────────────────────────────────────────────
-- Workspace members can read corrections
DROP POLICY IF EXISTS "corrections_workspace_read" ON reviewer_corrections;
CREATE POLICY "corrections_workspace_read" ON reviewer_corrections
  FOR SELECT USING (firm_workspace_id = auth_user_workspace_id());

-- Reviewers + can insert corrections
DROP POLICY IF EXISTS "corrections_reviewer_insert" ON reviewer_corrections;
CREATE POLICY "corrections_reviewer_insert" ON reviewer_corrections
  FOR INSERT WITH CHECK (
    firm_workspace_id = auth_user_workspace_id()
    AND reviewer_id = auth.uid()
    AND auth_user_role() IN ('reviewer', 'compliance_officer', 'admin')
  );

-- ── 4g. audit_log ────────────────────────────────────────────────────────────
-- Compliance officers and admins can read audit log for their workspace
DROP POLICY IF EXISTS "audit_log_workspace_read" ON audit_log;
CREATE POLICY "audit_log_workspace_read" ON audit_log
  FOR SELECT USING (
    firm_workspace_id = auth_user_workspace_id()
    AND auth_user_role() IN ('compliance_officer', 'admin')
  );

-- Backend service role inserts audit log (bypasses RLS via service key)
-- No INSERT policy needed — service role bypasses RLS

-- ── 5. Auto-enqueue trigger: new structure → review_queue 'pending' ───────────
-- FR-6.1: Newly generated structures enter review_queue as unvalidated by default
CREATE OR REPLACE FUNCTION auto_enqueue_structure_review()
RETURNS TRIGGER AS $$
BEGIN
  -- Only auto-enqueue if the structure doesn't already have a review_queue entry
  IF NOT EXISTS (
    SELECT 1 FROM review_queue WHERE structure_id = NEW.id
  ) THEN
    INSERT INTO review_queue (structure_id, status, created_at, updated_at)
    VALUES (NEW.id, 'pending', NOW(), NOW());
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_auto_enqueue_structure ON structures;
CREATE TRIGGER trg_auto_enqueue_structure
  AFTER INSERT ON structures
  FOR EACH ROW
  EXECUTE FUNCTION auto_enqueue_structure_review();

-- ── 6. Auto-update structure status on review_queue change ────────────────────
-- When reviewer approves/flags/rejects in review_queue, sync to structures.status
CREATE OR REPLACE FUNCTION sync_structure_status_from_review()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'approved' THEN
    UPDATE structures SET status = 'approved', updated_at = NOW()
    WHERE id = NEW.structure_id;
  ELSIF NEW.status = 'flagged' THEN
    UPDATE structures SET status = 'flagged', updated_at = NOW()
    WHERE id = NEW.structure_id;
  ELSIF NEW.status = 'in_review' THEN
    UPDATE structures SET status = 'under_review', updated_at = NOW()
    WHERE id = NEW.structure_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_sync_structure_status ON review_queue;
CREATE TRIGGER trg_sync_structure_status
  AFTER UPDATE OF status ON review_queue
  FOR EACH ROW
  EXECUTE FUNCTION sync_structure_status_from_review();

-- ── 7. Supabase Auth: auto-create user profile on sign-up ────────────────────
-- When a user signs up via Supabase Auth, insert a row into public.users
CREATE OR REPLACE FUNCTION handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, role, is_active, created_at)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    'associate',   -- Default role; admin promotes as needed
    TRUE,
    NOW()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach to auth.users (Supabase managed table)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_auth_user();

-- ══════════════════════════════════════════════════════════════════════════════
-- Done.
-- New: reviewer_corrections, RLS policies on all tables, auto-enqueue trigger,
--      structure status sync trigger, auth user auto-profile trigger.
-- ══════════════════════════════════════════════════════════════════════════════
