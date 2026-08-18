from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.models.food_knowledge import (
    FoodDataSourceRecord,
    FoodItemRecord,
    FoodAliasRecord,
)
from app.food_knowledge.normalization import normalize_food_search_query


class FoodRepository:
    """
    Persistence layer for Reference Food Knowledge.
    Ensures structured queries, eager-loading, and isolation from pure engine calculations.
    """

    @staticmethod
    def get_or_create_source(
        db: Session,
        code: str,
        name: str,
        publisher: Optional[str] = None,
        edition: Optional[str] = None,
        publication_year: Optional[int] = None,
        source_type: str = "FOOD_COMPOSITION_TABLE",
        reference_url: Optional[str] = None,
        license_status: Optional[str] = None,
        license_notes: Optional[str] = None,
        checksum: Optional[str] = None,
    ) -> FoodDataSourceRecord:
        source = db.query(FoodDataSourceRecord).filter(FoodDataSourceRecord.code == code).first()
        if not source:
            source = FoodDataSourceRecord(
                code=code,
                name=name,
                publisher=publisher,
                edition=edition,
                publication_year=publication_year,
                source_type=source_type,
                reference_url=reference_url,
                license_status=license_status,
                license_notes=license_notes,
                checksum=checksum,
            )
            db.add(source)
            db.commit()
            db.refresh(source)
        return source

    @staticmethod
    def get_source_by_code(db: Session, code: str) -> Optional[FoodDataSourceRecord]:
        return db.query(FoodDataSourceRecord).filter(FoodDataSourceRecord.code == code).first()

    @staticmethod
    def get_food_by_id(db: Session, food_id: str) -> Optional[FoodItemRecord]:
        return (
            db.query(FoodItemRecord)
            .options(
                joinedload(FoodItemRecord.source),
                joinedload(FoodItemRecord.nutrients),
                joinedload(FoodItemRecord.aliases),
                joinedload(FoodItemRecord.servings),
                joinedload(FoodItemRecord.allergens),
                joinedload(FoodItemRecord.preparation_requirements),
            )
            .filter(FoodItemRecord.id == food_id)
            .first()
        )

    @staticmethod
    def get_food_by_source_code(db: Session, source_id: str, source_food_code: str) -> Optional[FoodItemRecord]:
        return (
            db.query(FoodItemRecord)
            .filter(
                FoodItemRecord.source_id == source_id,
                FoodItemRecord.source_food_code == source_food_code,
            )
            .first()
        )

    @staticmethod
    def search_foods(
        db: Session,
        query: str,
        category: Optional[str] = None,
        is_active_only: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> List[FoodItemRecord]:
        normalized_q = normalize_food_search_query(query)
        
        stmt = db.query(FoodItemRecord).options(
            joinedload(FoodItemRecord.source),
            joinedload(FoodItemRecord.nutrients),
            joinedload(FoodItemRecord.aliases),
            joinedload(FoodItemRecord.servings),
            joinedload(FoodItemRecord.allergens),
            joinedload(FoodItemRecord.preparation_requirements),
        )

        if normalized_q:
            filters = [
                FoodItemRecord.normalized_name.contains(normalized_q),
                FoodItemRecord.canonical_name.ilike(f"%{query.strip()}%"),
                FoodItemRecord.aliases.any(FoodAliasRecord.normalized_alias.contains(normalized_q)),
                FoodItemRecord.aliases.any(FoodAliasRecord.alias.ilike(f"%{query.strip()}%")),
            ]
            stmt = stmt.filter(or_(*filters))

        if category:
            stmt = stmt.filter(FoodItemRecord.food_category == category.upper())
        if is_active_only:
            stmt = stmt.filter(FoodItemRecord.is_active.is_(True))

        return stmt.order_by(FoodItemRecord.canonical_name).offset(offset).limit(limit).all()
