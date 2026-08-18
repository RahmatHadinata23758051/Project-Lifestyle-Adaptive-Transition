import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class FoodDataSourceRecord(Base):
    __tablename__ = "food_data_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    publisher = Column(String(255), nullable=True)
    edition = Column(String(50), nullable=True)
    publication_year = Column(Integer, nullable=True)
    source_type = Column(String(50), nullable=False, default="FOOD_COMPOSITION_TABLE")
    reference_url = Column(String(500), nullable=True)
    license_status = Column(String(100), nullable=True)
    license_notes = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    food_items = relationship("FoodItemRecord", back_populates="source", cascade="all, delete-orphan")


class FoodItemRecord(Base):
    __tablename__ = "food_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, index=True)
    local_name = Column(String(255), nullable=True)
    scientific_name = Column(String(255), nullable=True)
    entity_type = Column(String(50), nullable=False, default="GENERIC_FOOD")
    food_category = Column(String(50), nullable=False, index=True)
    preparation_state = Column(String(50), nullable=False, default="RAW")
    is_generic_food = Column(Boolean, default=True, nullable=False)
    source_id = Column(String(36), ForeignKey("food_data_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    source_food_code = Column(String(50), nullable=True, index=True)
    data_quality_status = Column(String(50), nullable=False, default="VERIFIED_OFFICIAL")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    source = relationship("FoodDataSourceRecord", back_populates="food_items")
    nutrients = relationship("FoodNutrientsRecord", back_populates="food_item", uselist=False, cascade="all, delete-orphan")
    aliases = relationship("FoodAliasRecord", back_populates="food_item", cascade="all, delete-orphan")
    servings = relationship("FoodServingRecord", back_populates="food_item", cascade="all, delete-orphan")
    allergens = relationship("FoodItemAllergenRecord", back_populates="food_item", cascade="all, delete-orphan")
    preparation_requirements = relationship("FoodPreparationRequirementRecord", back_populates="food_item", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_id", "source_food_code", name="uq_food_items_source_code"),
    )


class FoodNutrientsRecord(Base):
    __tablename__ = "food_nutrients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    food_item_id = Column(String(36), ForeignKey("food_items.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    energy_kcal = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    carbohydrate_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    water_g = Column(Float, nullable=True)
    optional_micronutrients_json = Column(JSON, nullable=True)
    basis_type = Column(String(50), nullable=False, default="PER_100_G_EDIBLE")
    reference_amount = Column(Float, nullable=False, default=100.0)
    reference_unit = Column(String(20), nullable=False, default="g")
    edible_portion_percent = Column(Float, nullable=True)
    data_quality_status = Column(String(50), nullable=False, default="VERIFIED_OFFICIAL")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    food_item = relationship("FoodItemRecord", back_populates="nutrients")


class FoodAliasRecord(Base):
    __tablename__ = "food_aliases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    food_item_id = Column(String(36), ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    alias = Column(String(255), nullable=False, index=True)
    normalized_alias = Column(String(255), nullable=False, index=True)
    language = Column(String(10), default="id", nullable=False)
    region = Column(String(100), nullable=True)
    alias_type = Column(String(50), nullable=False, default="COMMON_NAME")

    food_item = relationship("FoodItemRecord", back_populates="aliases")


class FoodServingRecord(Base):
    __tablename__ = "food_servings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    food_item_id = Column(String(36), ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    serving_name = Column(String(100), nullable=False)
    grams = Column(Float, nullable=False)
    source_type = Column(String(50), nullable=False, default="MEASURED_CURATED")
    confidence = Column(String(50), nullable=False, default="HIGH")
    region = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    food_item = relationship("FoodItemRecord", back_populates="servings")


class FoodItemAllergenRecord(Base):
    __tablename__ = "food_item_allergens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    food_item_id = Column(String(36), ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen_type = Column(String(50), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False, default="CONTAINS")
    notes = Column(Text, nullable=True)

    food_item = relationship("FoodItemRecord", back_populates="allergens")

    __table_args__ = (
        UniqueConstraint("food_item_id", "allergen_type", name="uq_food_item_allergen"),
    )


class FoodPreparationRequirementRecord(Base):
    __tablename__ = "food_preparation_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    food_item_id = Column(String(36), ForeignKey("food_items.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    requires_cooking = Column(Boolean, default=False, nullable=False)
    minimum_capability = Column(String(50), nullable=False, default="CAN_COOK")
    prep_complexity = Column(String(50), nullable=False, default="NONE")
    required_equipment_json = Column(JSON, nullable=True)

    food_item = relationship("FoodItemRecord", back_populates="preparation_requirements")
