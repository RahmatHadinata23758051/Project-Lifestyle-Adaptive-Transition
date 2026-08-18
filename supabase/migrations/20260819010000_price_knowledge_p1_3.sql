-- ============================================================================
-- Migration: Price Knowledge Foundation P1.3
-- Version: 20260819010000
-- Description: Price sources, food price observations with unit basis,
--              location, freshness, confidence, scope isolation, and import history.
-- ============================================================================

-- 1. Food Price Sources
CREATE TABLE IF NOT EXISTS public.food_price_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'MANUAL_CURATED',
    publisher VARCHAR(150),
    license_note TEXT,
    source_reference VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2. Food Price Observations
CREATE TABLE IF NOT EXISTS public.food_price_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_item_id UUID NOT NULL REFERENCES public.food_items(id) ON DELETE CASCADE,
    source_id UUID REFERENCES public.food_price_sources(id) ON DELETE SET NULL,
    owner_user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    scope_type VARCHAR(50) NOT NULL DEFAULT 'GLOBAL_REFERENCE',
    amount DOUBLE PRECISION NOT NULL,
    unit VARCHAR(50) NOT NULL,
    price_idr INTEGER NOT NULL,
    currency_code VARCHAR(10) NOT NULL DEFAULT 'IDR',
    price_basis VARCHAR(50) NOT NULL DEFAULT 'AS_SOLD',
    country VARCHAR(50) NOT NULL DEFAULT 'ID',
    province VARCHAR(100),
    city_regency VARCHAR(100),
    district VARCHAR(100),
    location_detail VARCHAR(255),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    is_promotional BOOLEAN NOT NULL DEFAULT false,
    confidence VARCHAR(50) NOT NULL DEFAULT 'HIGH',
    quality_status VARCHAR(50) NOT NULL DEFAULT 'VERIFIED',
    package_quantity_grams DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_price_obs_food_item ON public.food_price_observations (food_item_id);
CREATE INDEX IF NOT EXISTS idx_price_obs_scope_owner ON public.food_price_observations (scope_type, owner_user_id);
CREATE INDEX IF NOT EXISTS idx_price_obs_location ON public.food_price_observations (country, province, city_regency);
CREATE INDEX IF NOT EXISTS idx_price_obs_observed_at ON public.food_price_observations (observed_at DESC);

-- 3. Food Price Import Runs
CREATE TABLE IF NOT EXISTS public.food_price_import_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES public.food_price_sources(id) ON DELETE SET NULL,
    total_records INTEGER NOT NULL DEFAULT 0,
    inserted_records INTEGER NOT NULL DEFAULT 0,
    rejected_records INTEGER NOT NULL DEFAULT 0,
    is_dry_run BOOLEAN NOT NULL DEFAULT false,
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- ============================================================================
-- Row Level Security (RLS) Policies
-- ============================================================================

ALTER TABLE public.food_price_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_price_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_price_import_runs ENABLE ROW LEVEL SECURITY;

-- Sources: Global read-only for authenticated users
CREATE POLICY "Allow authenticated read price sources"
    ON public.food_price_sources FOR SELECT
    TO authenticated
    USING (true);

-- Observations: Users can view global reference prices AND their own private observations
CREATE POLICY "Allow read global reference or owned private prices"
    ON public.food_price_observations FOR SELECT
    TO authenticated
    USING (
        scope_type = 'GLOBAL_REFERENCE'
        OR (scope_type = 'USER_PRIVATE' AND auth.uid() = owner_user_id)
    );

CREATE POLICY "Allow user insert own private prices"
    ON public.food_price_observations FOR INSERT
    TO authenticated
    WITH CHECK (
        scope_type = 'USER_PRIVATE' AND auth.uid() = owner_user_id
    );

CREATE POLICY "Allow user update own private prices"
    ON public.food_price_observations FOR UPDATE
    TO authenticated
    USING (
        scope_type = 'USER_PRIVATE' AND auth.uid() = owner_user_id
    );

CREATE POLICY "Allow user delete own private prices"
    ON public.food_price_observations FOR DELETE
    TO authenticated
    USING (
        scope_type = 'USER_PRIVATE' AND auth.uid() = owner_user_id
    );
