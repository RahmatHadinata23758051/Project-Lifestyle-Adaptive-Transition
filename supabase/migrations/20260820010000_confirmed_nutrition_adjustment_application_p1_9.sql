-- Phase P1.9: Confirmed Nutrition Adjustment Application Migration
-- Tables: nutrition_state_revisions, nutrition_adjustment_applications

CREATE TABLE IF NOT EXISTS nutrition_state_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    revision_number INTEGER NOT NULL,
    previous_revision_id UUID,
    source_type VARCHAR(50) NOT NULL DEFAULT 'USER_CONFIRMED_ADJUSTMENT',
    source_reference_id VARCHAR(50),
    target_energy_kcal INTEGER NOT NULL,
    goal_type VARCHAR(50) NOT NULL DEFAULT 'NUTRITION_WEIGHT_GAIN',
    effective_from TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_owner_nutrition_revision UNIQUE (owner_user_id, revision_number)
);

CREATE INDEX IF NOT EXISTS idx_state_rev_owner ON nutrition_state_revisions(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_state_rev_num ON nutrition_state_revisions(revision_number);

-- Enable RLS for state revisions
ALTER TABLE nutrition_state_revisions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own nutrition state revisions"
    ON nutrition_state_revisions
    FOR ALL
    USING (auth.uid() = owner_user_id)
    WITH CHECK (auth.uid() = owner_user_id);


CREATE TABLE IF NOT EXISTS nutrition_adjustment_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    proposal_id UUID NOT NULL UNIQUE,
    idempotency_key VARCHAR(128) NOT NULL,
    previous_state_revision INTEGER NOT NULL,
    new_state_revision INTEGER NOT NULL,
    previous_target_kcal INTEGER NOT NULL,
    applied_target_kcal INTEGER NOT NULL,
    delta_kcal INTEGER NOT NULL,
    application_status VARCHAR(50) NOT NULL DEFAULT 'APPLIED',
    downstream_invalidation JSONB NOT NULL DEFAULT '{}'::jsonb,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    policy_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_owner_idempotency_key UNIQUE (owner_user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_adj_app_owner ON nutrition_adjustment_applications(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_adj_app_proposal ON nutrition_adjustment_applications(proposal_id);
CREATE INDEX IF NOT EXISTS idx_adj_app_idempotency ON nutrition_adjustment_applications(idempotency_key);

-- Enable RLS for applications
ALTER TABLE nutrition_adjustment_applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own nutrition adjustment applications"
    ON nutrition_adjustment_applications
    FOR ALL
    USING (auth.uid() = owner_user_id)
    WITH CHECK (auth.uid() = owner_user_id);
