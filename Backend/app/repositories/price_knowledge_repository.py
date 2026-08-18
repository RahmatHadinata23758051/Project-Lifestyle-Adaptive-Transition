from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.price_knowledge import (
    FoodPriceSourceRecord,
    FoodPriceObservationRecord,
    FoodPriceImportRunRecord,
)
from app.price_knowledge.constants import (
    PriceUnit,
    PriceBasis,
    PriceSourceType,
    PriceScopeType,
    PriceQuality,
    PriceConfidence,
)
from app.price_knowledge.models import LocationDTO, FoodPriceObservationDTO


class PriceKnowledgeRepository:
    """
    Repository layer for Price Knowledge database operations with RLS ownership isolation.
    """

    @staticmethod
    def get_or_create_source(
        db: Session,
        name: str,
        source_type: PriceSourceType = PriceSourceType.MANUAL_CURATED,
        publisher: Optional[str] = None,
        source_reference: Optional[str] = None,
    ) -> FoodPriceSourceRecord:
        source = db.query(FoodPriceSourceRecord).filter_by(name=name).first()
        if not source:
            source = FoodPriceSourceRecord(
                name=name,
                source_type=source_type,
                publisher=publisher,
                source_reference=source_reference,
            )
            db.add(source)
            db.commit()
            db.refresh(source)
        return source

    @classmethod
    def record_to_dto(cls, record: FoodPriceObservationRecord) -> FoodPriceObservationDTO:
        loc = LocationDTO(
            country=record.country,
            province=record.province,
            city_regency=record.city_regency,
            district=record.district,
            market_or_store=record.location_detail,
        )
        return FoodPriceObservationDTO(
            id=record.id,
            food_item_id=record.food_item_id,
            amount=record.amount,
            unit=PriceUnit(record.unit),
            price_idr=record.price_idr,
            currency_code=record.currency_code,
            price_basis=PriceBasis(record.price_basis),
            source_type=PriceSourceType(record.source.source_type) if record.source else PriceSourceType.MANUAL_CURATED,
            source_id=record.source_id,
            source_reference=record.source.source_reference if record.source else None,
            observed_at=record.observed_at,
            location=loc,
            scope_type=PriceScopeType(record.scope_type),
            owner_user_id=record.owner_user_id,
            valid_from=record.valid_from,
            valid_until=record.valid_until,
            is_promotional=record.is_promotional,
            confidence=PriceConfidence(record.confidence),
            quality_status=PriceQuality(record.quality_status),
            package_quantity_grams=record.package_quantity_grams,
        )

    @classmethod
    def get_observations_for_food(
        cls,
        db: Session,
        food_item_id: str,
        user_id: Optional[str] = None,
    ) -> List[FoodPriceObservationDTO]:
        """
        Retrieves global reference observations + user's own private observations.
        Guarantees User A cannot see User B's private price records (RLS).
        """
        query = db.query(FoodPriceObservationRecord).filter(
            FoodPriceObservationRecord.food_item_id == food_item_id
        )

        if user_id:
            query = query.filter(
                or_(
                    FoodPriceObservationRecord.scope_type == PriceScopeType.GLOBAL_REFERENCE,
                    and_(
                        FoodPriceObservationRecord.scope_type == PriceScopeType.USER_PRIVATE,
                        FoodPriceObservationRecord.owner_user_id == user_id,
                    ),
                )
            )
        else:
            query = query.filter(FoodPriceObservationRecord.scope_type == PriceScopeType.GLOBAL_REFERENCE)

        records = query.order_by(FoodPriceObservationRecord.observed_at.desc()).all()
        return [cls.record_to_dto(r) for r in records]

    @classmethod
    def get_observations_for_foods(
        cls,
        db: Session,
        food_item_ids: List[str],
        user_id: Optional[str] = None,
    ) -> List[FoodPriceObservationDTO]:
        if not food_item_ids:
            return []

        query = db.query(FoodPriceObservationRecord).filter(
            FoodPriceObservationRecord.food_item_id.in_(food_item_ids)
        )

        if user_id:
            query = query.filter(
                or_(
                    FoodPriceObservationRecord.scope_type == PriceScopeType.GLOBAL_REFERENCE,
                    and_(
                        FoodPriceObservationRecord.scope_type == PriceScopeType.USER_PRIVATE,
                        FoodPriceObservationRecord.owner_user_id == user_id,
                    ),
                )
            )
        else:
            query = query.filter(FoodPriceObservationRecord.scope_type == PriceScopeType.GLOBAL_REFERENCE)

        records = query.order_by(FoodPriceObservationRecord.observed_at.desc()).all()
        return [cls.record_to_dto(r) for r in records]

    @classmethod
    def add_observation(
        cls,
        db: Session,
        food_item_id: str,
        amount: float,
        unit: PriceUnit,
        price_idr: int,
        source_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        scope_type: PriceScopeType = PriceScopeType.GLOBAL_REFERENCE,
        price_basis: PriceBasis = PriceBasis.AS_SOLD,
        location: Optional[LocationDTO] = None,
        observed_at: Optional[Any] = None,
        is_promotional: bool = False,
        confidence: PriceConfidence = PriceConfidence.HIGH,
        quality_status: PriceQuality = PriceQuality.VERIFIED,
        package_quantity_grams: Optional[float] = None,
    ) -> FoodPriceObservationRecord:
        loc = location or LocationDTO()
        record = FoodPriceObservationRecord(
            food_item_id=food_item_id,
            source_id=source_id,
            owner_user_id=owner_user_id,
            scope_type=scope_type,
            amount=amount,
            unit=unit,
            price_idr=price_idr,
            price_basis=price_basis,
            country=loc.country,
            province=loc.province,
            city_regency=loc.city_regency,
            district=loc.district,
            location_detail=loc.market_or_store,
            observed_at=observed_at or datetime.utcnow(),
            is_promotional=is_promotional,
            confidence=confidence,
            quality_status=quality_status,
            package_quantity_grams=package_quantity_grams,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
