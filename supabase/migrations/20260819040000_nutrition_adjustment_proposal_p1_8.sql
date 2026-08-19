-- Phase P1.8: Nutrition Adjustment Proposal Engine Migration
-- Table: nutrition_adjustment_proposals

CREATE TABLE IF NOT EXISTS nutrition_adjustment_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    evaluation_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    lifecycle_state VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    proposal_type VARCHAR(50) NOT NULL,
    current_target_kcal FLOAT NOT NULL,
    proposed_target_kcal FLOAT NOT NULL,
    delta_kcal FLOAT NOT NULL,
    confidence VARCHAR(20) NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    evidence_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanations JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    expires_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    rejection_reason VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_adjustment_prop_owner ON nutrition_adjustment_proposals(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_adjustment_prop_eval ON nutrition_adjustment_proposals(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_adjustment_prop_fingerprint ON nutrition_adjustment_proposals(fingerprint);
CREATE INDEX IF NOT EXISTS idx_adjustment_prop_lifecycle ON nutrition_adjustment_proposals(lifecycle_state);

-- Enable RLS
ALTER TABLE nutrition_adjustment_proposals ENABLE ROW LEVEL SECURITY;

-- RLS Policy (Private to owner)
CREATE POLICY "Users can manage own adjustment proposals"
    ON nutrition_adjustment_proposals
    FOR ALL
    USING (auth.uid() = owner_user_id)
    WITH CHECK (auth.uid() = owner_user_id);
