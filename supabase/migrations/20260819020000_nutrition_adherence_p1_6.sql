-- Phase P1.6: Nutrition Adherence & Daily Check-in Migration
-- Tables: nutrition_meal_checkins, nutrition_unplanned_intakes, nutrition_actual_items

-- Table 1: nutrition_meal_checkins
CREATE TABLE IF NOT EXISTS nutrition_meal_checkins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_id VARCHAR(100) NOT NULL,
    logical_day_id VARCHAR(50) NOT NULL,
    slot_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    meal_occurred_at VARCHAR(10),
    checked_in_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    actual_spend_idr INTEGER,
    deviation_reason VARCHAR(50),
    notes TEXT,
    certainty VARCHAR(20) NOT NULL DEFAULT 'EXACT',
    revision INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_meal_checkins_owner ON nutrition_meal_checkins(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_meal_checkins_plan ON nutrition_meal_checkins(plan_id);
CREATE INDEX IF NOT EXISTS idx_meal_checkins_logical_day ON nutrition_meal_checkins(logical_day_id);

-- Table 2: nutrition_unplanned_intakes
CREATE TABLE IF NOT EXISTS nutrition_unplanned_intakes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    logical_day_id VARCHAR(50) NOT NULL,
    occurred_at VARCHAR(10) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    actual_spend_idr INTEGER,
    reason VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_unplanned_intakes_owner ON nutrition_unplanned_intakes(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_unplanned_intakes_logical_day ON nutrition_unplanned_intakes(logical_day_id);

-- Table 3: nutrition_actual_items
CREATE TABLE IF NOT EXISTS nutrition_actual_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checkin_id UUID REFERENCES nutrition_meal_checkins(id) ON DELETE CASCADE,
    unplanned_intake_id UUID REFERENCES nutrition_unplanned_intakes(id) ON DELETE CASCADE,
    food_item_id VARCHAR(50),
    display_name VARCHAR(255) NOT NULL,
    serving_id VARCHAR(50),
    serving_name VARCHAR(100),
    quantity FLOAT NOT NULL DEFAULT 1.0,
    grams FLOAT,
    energy_kcal FLOAT,
    protein_g FLOAT,
    fat_g FLOAT,
    carbohydrate_g FLOAT,
    source_type VARCHAR(50) NOT NULL DEFAULT 'USER_REPORTED_UNRESOLVED',
    certainty VARCHAR(20) NOT NULL DEFAULT 'EXACT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_actual_items_checkin ON nutrition_actual_items(checkin_id);
CREATE INDEX IF NOT EXISTS idx_actual_items_unplanned ON nutrition_actual_items(unplanned_intake_id);

-- Enable RLS
ALTER TABLE nutrition_meal_checkins ENABLE ROW LEVEL SECURITY;
ALTER TABLE nutrition_unplanned_intakes ENABLE ROW LEVEL SECURITY;
ALTER TABLE nutrition_actual_items ENABLE ROW LEVEL SECURITY;

-- RLS Policies: nutrition_meal_checkins (User Private)
CREATE POLICY "Users can manage own meal checkins"
    ON nutrition_meal_checkins
    FOR ALL
    USING (auth.uid() = owner_user_id)
    WITH CHECK (auth.uid() = owner_user_id);

-- RLS Policies: nutrition_unplanned_intakes (User Private)
CREATE POLICY "Users can manage own unplanned intakes"
    ON nutrition_unplanned_intakes
    FOR ALL
    USING (auth.uid() = owner_user_id)
    WITH CHECK (auth.uid() = owner_user_id);

-- RLS Policies: nutrition_actual_items (User Private through checkin or unplanned ownership)
CREATE POLICY "Users can manage own actual items via checkin"
    ON nutrition_actual_items
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM nutrition_meal_checkins
            WHERE nutrition_meal_checkins.id = nutrition_actual_items.checkin_id
            AND nutrition_meal_checkins.owner_user_id = auth.uid()
        )
        OR
        EXISTS (
            SELECT 1 FROM nutrition_unplanned_intakes
            WHERE nutrition_unplanned_intakes.id = nutrition_actual_items.unplanned_intake_id
            AND nutrition_unplanned_intakes.owner_user_id = auth.uid()
        )
    );
