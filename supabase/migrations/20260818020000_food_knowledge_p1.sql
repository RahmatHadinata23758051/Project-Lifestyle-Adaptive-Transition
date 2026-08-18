-- ============================================================================
-- Migration: Food Knowledge Foundation P1
-- Version: 20260818020000
-- Description: Canonical food items, nutrient profiles with provenance and basis,
--              serving conversions, aliases, allergen safety metadata,
--              and preparation requirements.
-- ============================================================================

-- 1. Food Data Sources
CREATE TABLE IF NOT EXISTS public.food_data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    publisher VARCHAR(255),
    edition VARCHAR(50),
    publication_year INTEGER,
    source_type VARCHAR(50) NOT NULL DEFAULT 'FOOD_COMPOSITION_TABLE',
    reference_url VARCHAR(500),
    license_status VARCHAR(100),
    license_notes TEXT,
    checksum VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2. Food Items (Canonical Reference)
CREATE TABLE IF NOT EXISTS public.food_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    local_name VARCHAR(255),
    scientific_name VARCHAR(255),
    entity_type VARCHAR(50) NOT NULL DEFAULT 'GENERIC_FOOD',
    food_category VARCHAR(50) NOT NULL,
    preparation_state VARCHAR(50) NOT NULL DEFAULT 'RAW',
    is_generic_food BOOLEAN NOT NULL DEFAULT true,
    source_id UUID NOT NULL REFERENCES public.food_data_sources(id) ON DELETE CASCADE,
    source_food_code VARCHAR(50),
    data_quality_status VARCHAR(50) NOT NULL DEFAULT 'VERIFIED_OFFICIAL',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_food_items_source_code UNIQUE (source_id, source_food_code)
);

CREATE INDEX IF NOT EXISTS idx_food_items_canonical_name ON public.food_items (canonical_name);
CREATE INDEX IF NOT EXISTS idx_food_items_normalized_name ON public.food_items (normalized_name);
CREATE INDEX IF NOT EXISTS idx_food_items_category ON public.food_items (food_category);
CREATE INDEX IF NOT EXISTS idx_food_items_source_code ON public.food_items (source_food_code);

-- 3. Food Nutrients (Per basis)
CREATE TABLE IF NOT EXISTS public.food_nutrients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_item_id UUID UNIQUE NOT NULL REFERENCES public.food_items(id) ON DELETE CASCADE,
    energy_kcal DOUBLE PRECISION,
    protein_g DOUBLE PRECISION,
    fat_g DOUBLE PRECISION,
    carbohydrate_g DOUBLE PRECISION,
    fiber_g DOUBLE PRECISION,
    water_g DOUBLE PRECISION,
    optional_micronutrients_json JSONB,
    basis_type VARCHAR(50) NOT NULL DEFAULT 'PER_100_G_EDIBLE',
    reference_amount DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    reference_unit VARCHAR(20) NOT NULL DEFAULT 'g',
    edible_portion_percent DOUBLE PRECISION,
    data_quality_status VARCHAR(50) NOT NULL DEFAULT 'VERIFIED_OFFICIAL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 4. Food Aliases
CREATE TABLE IF NOT EXISTS public.food_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_item_id UUID NOT NULL REFERENCES public.food_items(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    normalized_alias VARCHAR(255) NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'id',
    region VARCHAR(100),
    alias_type VARCHAR(50) NOT NULL DEFAULT 'COMMON_NAME'
);

CREATE INDEX IF NOT EXISTS idx_food_aliases_alias ON public.food_aliases (alias);
CREATE INDEX IF NOT EXISTS idx_food_aliases_normalized ON public.food_aliases (normalized_alias);
CREATE INDEX IF NOT EXISTS idx_food_aliases_food_id ON public.food_aliases (food_item_id);

-- 5. Food Servings
CREATE TABLE IF NOT EXISTS public.food_servings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_item_id UUID NOT NULL REFERENCES public.food_items(id) ON DELETE CASCADE,
    serving_name VARCHAR(100) NOT NULL,
    grams DOUBLE PRECISION NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'MEASURED_CURATED',
    confidence VARCHAR(50) NOT NULL DEFAULT 'HIGH',
    region VARCHAR(100),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_food_servings_food_id ON public.food_servings (food_item_id);

-- 6. Food Item Allergens
CREATE TABLE IF NOT EXISTS public.food_item_allergens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_item_id UUID NOT NULL REFERENCES public.food_items(id) ON DELETE CASCADE,
    allergen_type VARCHAR(50) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL DEFAULT 'CONTAINS',
    notes TEXT,
    CONSTRAINT uq_food_item_allergen UNIQUE (food_item_id, allergen_type)
);

CREATE INDEX IF NOT EXISTS idx_food_item_allergens_type ON public.food_item_allergens (allergen_type);

-- 7. Food Preparation Requirements
CREATE TABLE IF NOT EXISTS public.food_preparation_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_item_id UUID UNIQUE NOT NULL REFERENCES public.food_items(id) ON DELETE CASCADE,
    requires_cooking BOOLEAN NOT NULL DEFAULT false,
    minimum_capability VARCHAR(50) NOT NULL DEFAULT 'CAN_COOK',
    prep_complexity VARCHAR(50) NOT NULL DEFAULT 'NONE',
    required_equipment_json JSONB
);

-- ============================================================================
-- Row Level Security (RLS) Policies
-- Reference tables have no user ownership. All authenticated users have SELECT access.
-- Insert/Update/Delete is restricted to service_role (Admin/Ingestion pipeline).
-- ============================================================================

ALTER TABLE public.food_data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_nutrients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_servings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_item_allergens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_preparation_requirements ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read access to all authenticated users for food_data_sources"
    ON public.food_data_sources FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow read access to all authenticated users for food_items"
    ON public.food_items FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow read access to all authenticated users for food_nutrients"
    ON public.food_nutrients FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow read access to all authenticated users for food_aliases"
    ON public.food_aliases FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow read access to all authenticated users for food_servings"
    ON public.food_servings FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow read access to all authenticated users for food_item_allergens"
    ON public.food_item_allergens FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow read access to all authenticated users for food_preparation_requirements"
    ON public.food_preparation_requirements FOR SELECT
    TO authenticated
    USING (true);
