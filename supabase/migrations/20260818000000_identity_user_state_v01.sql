-- ==============================================================================
-- Project Chronos — Identity & User State Foundation v0.1 Migration
-- Target: Supabase PostgreSQL with Row Level Security (RLS)
-- ==============================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Profiles Table (Application-level profile linked to auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name VARCHAR(100),
    birth_date VARCHAR(10),
    sex VARCHAR(20),
    timezone VARCHAR(50) DEFAULT 'Asia/Jakarta' NOT NULL,
    height_cm NUMERIC(5,2),
    current_weight_kg NUMERIC(5,2),
    occupation_type VARCHAR(50),
    onboarding_status VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 2. User Goals Table
CREATE TABLE IF NOT EXISTS public.user_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    domain VARCHAR(50) DEFAULT 'SLEEP_ROUTINE' NOT NULL,
    priority VARCHAR(50) DEFAULT 'PRIMARY' NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE' NOT NULL,
    target_description VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 3. Sleep Baselines Table (Preserves History with is_current)
CREATE TABLE IF NOT EXISTS public.sleep_baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    bedtime VARCHAR(5) NOT NULL,
    wake_time VARCHAR(5) NOT NULL,
    is_current BOOLEAN DEFAULT TRUE NOT NULL,
    captured_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 4. Financial Profiles Table
CREATE TABLE IF NOT EXISTS public.financial_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    weekly_food_budget NUMERIC(12,2) DEFAULT 350000.00 NOT NULL,
    currency VARCHAR(10) DEFAULT 'IDR' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 5. User Constraints Table
CREATE TABLE IF NOT EXISTS public.constraints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    category VARCHAR(50) DEFAULT 'PERSONAL' NOT NULL,
    day_of_week VARCHAR(20) DEFAULT 'MONDAY' NOT NULL,
    start_time VARCHAR(5) NOT NULL,
    end_time VARCHAR(5) NOT NULL,
    is_flexible BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 6. Historical Measurements Table
CREATE TABLE IF NOT EXISTS public.measurements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL,
    value NUMERIC(10,2),
    string_value VARCHAR(100),
    unit VARCHAR(20),
    captured_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- ==============================================================================
-- Row Level Security (RLS) Configuration (P0.11)
-- ==============================================================================

-- Enable RLS on all user-owned tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sleep_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.financial_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.constraints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.measurements ENABLE ROW LEVEL SECURITY;

-- Profiles RLS Policy
CREATE POLICY "Users can only view and edit own profile"
    ON public.profiles
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- User Goals RLS Policy
CREATE POLICY "Users can only view and edit own goals"
    ON public.user_goals
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Sleep Baselines RLS Policy
CREATE POLICY "Users can only view and insert own sleep baselines"
    ON public.sleep_baselines
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Financial Profiles RLS Policy
CREATE POLICY "Users can only view and edit own financial profile"
    ON public.financial_profiles
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Constraints RLS Policy
CREATE POLICY "Users can only view and edit own constraints"
    ON public.constraints
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Measurements RLS Policy
CREATE POLICY "Users can only view and insert own measurements"
    ON public.measurements
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Indexes for high performance isolation
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON public.profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_goals_user_id ON public.user_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_sleep_baselines_user_id ON public.sleep_baselines(user_id);
CREATE INDEX IF NOT EXISTS idx_financial_profiles_user_id ON public.financial_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_constraints_user_id ON public.constraints(user_id);
CREATE INDEX IF NOT EXISTS idx_measurements_user_id ON public.measurements(user_id);
