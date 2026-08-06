-- Sententia.ai — Audit Log Migration
-- FR-4.3: Log every compliance check deterministically

CREATE TABLE IF NOT EXISTS public.audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Corridor identification
    corridor_id         TEXT NOT NULL,
    policy_package      TEXT NOT NULL,
    evaluation_mode     TEXT NOT NULL,  -- 'opa_server' | 'opa_subprocess' | 'python_native'

    -- Linked objects (optional)
    scenario_id         UUID REFERENCES public.scenarios(id) ON DELETE SET NULL,
    structure_rank      INTEGER,

    -- Policy input / output
    input_data          JSONB NOT NULL,
    violations          JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings            JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_approvals  JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Decision
    is_allowed          BOOLEAN NOT NULL,
    is_rule_validated   BOOLEAN NOT NULL DEFAULT TRUE,
    blocking_count      INTEGER NOT NULL DEFAULT 0,
    warning_count       INTEGER NOT NULL DEFAULT 0
);

-- Index for scenario lookups (audit trail per scenario)
CREATE INDEX IF NOT EXISTS idx_audit_log_scenario_id
    ON public.audit_log(scenario_id)
    WHERE scenario_id IS NOT NULL;

-- Index for corridor analytics
CREATE INDEX IF NOT EXISTS idx_audit_log_corridor_id
    ON public.audit_log(corridor_id);

-- Index for time-range queries
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at
    ON public.audit_log(created_at DESC);

-- RLS: authenticated users can read their own logs; service role can write
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can manage audit_log"
    ON public.audit_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Authenticated users can read audit_log"
    ON public.audit_log
    FOR SELECT
    TO authenticated
    USING (true);
