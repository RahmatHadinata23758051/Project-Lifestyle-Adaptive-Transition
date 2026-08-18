-- ==============================================================================
-- Project Chronos — Dynamic Assessment Architecture v0.1 Migration
-- Target: Supabase PostgreSQL with Row Level Security (RLS)
-- ==============================================================================

-- 1. Nutrition Baselines Table
CREATE TABLE IF NOT EXISTS public.nutrition_baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    meals_per_day INT DEFAULT 3 NOT NULL,
    cooking_capability VARCHAR(50) DEFAULT 'LIMITED' NOT NULL,
    allergies VARCHAR(255) DEFAULT 'NONE' NOT NULL,
    food_restrictions VARCHAR(255),
    food_preferences VARCHAR(255),
    target_weight_kg NUMERIC(5,2),
    is_current BOOLEAN DEFAULT TRUE NOT NULL,
    captured_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 2. Physical Activity Baselines Table
CREATE TABLE IF NOT EXISTS public.activity_baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    experience_level VARCHAR(50) DEFAULT 'BEGINNER' NOT NULL,
    available_days_per_week INT DEFAULT 3 NOT NULL,
    minutes_per_session INT DEFAULT 30 NOT NULL,
    equipment_list TEXT DEFAULT 'NONE' NOT NULL,
    physical_limitations VARCHAR(255) DEFAULT 'NONE' NOT NULL,
    available_space VARCHAR(50),
    workout_preference VARCHAR(50),
    is_current BOOLEAN DEFAULT TRUE NOT NULL,
    captured_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 3. Immutable Assessment Snapshots Table
CREATE TABLE IF NOT EXISTS public.assessment_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- ==============================================================================
-- Row Level Security (RLS) Policies
-- ==============================================================================

ALTER TABLE public.nutrition_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only view and insert own nutrition baselines"
    ON public.nutrition_baselines
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can only view and insert own activity baselines"
    ON public.activity_baselines
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can only view and create own assessment snapshots"
    ON public.assessment_snapshots
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_nutrition_baselines_user_id ON public.nutrition_baselines(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_baselines_user_id ON public.activity_baselines(user_id);
CREATE INDEX IF NOT EXISTS idx_assessment_snapshots_user_id ON public.assessment_snapshots(user_id);
