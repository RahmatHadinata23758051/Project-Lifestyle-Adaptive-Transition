-- Phase P1.7: Nutrition Adaptation Evaluation Migration
-- Table: nutrition_adaptation_evaluations

CREATE TABLE IF NOT EXISTS nutrition_adaptation_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    decision VARCHAR(50) NOT NULL,
    review_domain VARCHAR(50) NOT NULL,
    confidence VARCHAR(20) NOT NULL,
    window_start VARCHAR(20) NOT NULL,
    window_end VARCHAR(20) NOT NULL,
    total_days INTEGER NOT NULL,
    usable_days INTEGER NOT NULL,
    weight_measurements_count INTEGER NOT NULL,
    slope_kg_per_day FLOAT,
    weight_direction VARCHAR(30) NOT NULL,
    adherence_category VARCHAR(50) NOT NULL,
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanations JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_adaptation_eval_owner ON nutrition_adaptation_evaluations(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_adaptation_eval_evaluated_at ON nutrition_adaptation_evaluations(evaluated_at);

-- Enable RLS
ALTER TABLE nutrition_adaptation_evaluations ENABLE ROW LEVEL SECURITY;

-- RLS Policies (User Private)
CREATE POLICY "Users can manage own adaptation evaluations"
    ON nutrition_adaptation_evaluations
    FOR ALL
    USING (auth.uid() = owner_user_id)
    WITH CHECK (auth.uid() = owner_user_id);
