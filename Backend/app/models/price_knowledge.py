import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Enum as SAEnum,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.price_knowledge.constants import (
    PriceUnit,
    PriceBasis,
    PriceSourceType,
    PriceScopeType,
    PriceQuality,
    PriceConfidence,
)


class FoodPriceSourceRecord(Base):
    __tablename__ = "food_price_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(150), nullable=False)
    source_type = Column(SAEnum(PriceSourceType), nullable=False, default=PriceSourceType.MANUAL_CURATED)
    publisher = Column(String(150), nullable=True)
    license_note = Column(Text, nullable=True)
    source_reference = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    observations = relationship("FoodPriceObservationRecord", back_populates="source", cascade="all, delete-orphan")


class FoodPriceObservationRecord(Base):
    __tablename__ = "food_price_observations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    food_item_id = Column(String(36), ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(36), ForeignKey("food_price_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    owner_user_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    scope_type = Column(SAEnum(PriceScopeType), nullable=False, default=PriceScopeType.GLOBAL_REFERENCE, index=True)

    amount = Column(Float, nullable=False)
    unit = Column(SAEnum(PriceUnit), nullable=False)
    price_idr = Column(Integer, nullable=False)
    currency_code = Column(String(10), nullable=False, default="IDR")
    price_basis = Column(SAEnum(PriceBasis), nullable=False, default=PriceBasis.AS_SOLD)

    country = Column(String(50), nullable=False, default="ID")
    province = Column(String(100), nullable=True, index=True)
    city_regency = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True)
    location_detail = Column(String(255), nullable=True)

    observed_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)

    is_promotional = Column(Boolean, default=False, nullable=False)
    confidence = Column(SAEnum(PriceConfidence), default=PriceConfidence.HIGH, nullable=False)
    quality_status = Column(SAEnum(PriceQuality), default=PriceQuality.VERIFIED, nullable=False)
    package_quantity_grams = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source = relationship("FoodPriceSourceRecord", back_populates="observations")
    food_item = relationship("FoodItemRecord")


class FoodPriceImportRunRecord(Base):
    __tablename__ = "food_price_import_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("food_price_sources.id", ondelete="SET NULL"), nullable=True)
    total_records = Column(Integer, default=0, nullable=False)
    inserted_records = Column(Integer, default=0, nullable=False)
    rejected_records = Column(Integer, default=0, nullable=False)
    is_dry_run = Column(Boolean, default=False, nullable=False)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
