from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.price_knowledge import (
    FoodPriceSourceRecord,
    FoodPriceObservationRecord,
    FoodPriceImportRunRecord,
)
from app.price_knowledge.constants import (
    PriceUnit,
    PriceBasis,
    PriceScopeType,
    PriceQuality,
    PriceConfidence,
)


class PriceImportPipeline:
    """
    Idempotent and validated batch price import pipeline (P1.3).
    """

    @classmethod
    def import_price_dataset(
        cls,
        db: Session,
        source_record: FoodPriceSourceRecord,
        raw_items: List[Dict[str, Any]],
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        inserted_count = 0
        rejected_count = 0
        rejection_reasons: List[str] = []

        for item in raw_items:
            food_item_id = item.get("food_item_id")
            amount = item.get("amount")
            unit_str = item.get("unit")
            price_idr = item.get("price_idr")

            # Validation
            if not food_item_id:
                rejected_count += 1
                rejection_reasons.append("Missing food_item_id")
                continue

            if amount is None or amount <= 0:
                rejected_count += 1
                rejection_reasons.append(f"Invalid amount {amount} for food {food_item_id}")
                continue

            if price_idr is None or price_idr <= 0:
                rejected_count += 1
                rejection_reasons.append(f"Invalid price_idr {price_idr} for food {food_item_id}")
                continue

            try:
                unit = PriceUnit(unit_str)
            except (ValueError, TypeError):
                rejected_count += 1
                rejection_reasons.append(f"Invalid unit {unit_str} for food {food_item_id}")
                continue

            observed_at = item.get("observed_at") or datetime.utcnow()
            city_regency = item.get("city_regency")

            # Idempotency check: avoid duplicate identical observation for same source + date + location
            existing = (
                db.query(FoodPriceObservationRecord)
                .filter_by(
                    source_id=source_record.id,
                    food_item_id=food_item_id,
                    amount=amount,
                    unit=unit,
                    price_idr=price_idr,
                    city_regency=city_regency,
                )
                .first()
            )
            if existing:
                continue  # Idempotent skip

            if not dry_run:
                obs = FoodPriceObservationRecord(
                    food_item_id=food_item_id,
                    source_id=source_record.id,
                    amount=amount,
                    unit=unit,
                    price_idr=price_idr,
                    currency_code=item.get("currency_code", "IDR"),
                    price_basis=PriceBasis(item.get("price_basis", PriceBasis.AS_SOLD)),
                    country=item.get("country", "ID"),
                    province=item.get("province"),
                    city_regency=city_regency,
                    district=item.get("district"),
                    location_detail=item.get("location_detail"),
                    observed_at=observed_at,
                    is_promotional=item.get("is_promotional", False),
                    confidence=PriceConfidence(item.get("confidence", PriceConfidence.HIGH)),
                    quality_status=PriceQuality(item.get("quality_status", PriceQuality.VERIFIED)),
                    package_quantity_grams=item.get("package_quantity_grams"),
                    scope_type=PriceScopeType.GLOBAL_REFERENCE,
                )
                db.add(obs)

            inserted_count += 1

        if not dry_run and inserted_count > 0:
            db.commit()

        # Record import run history
        if not dry_run:
            run_rec = FoodPriceImportRunRecord(
                source_id=source_record.id,
                total_records=len(raw_items),
                inserted_records=inserted_count,
                rejected_records=rejected_count,
                is_dry_run=dry_run,
                error_summary="; ".join(rejection_reasons[:10]) if rejection_reasons else None,
            )
            db.add(run_rec)
            db.commit()

        return {
            "source_id": source_record.id,
            "total_records": len(raw_items),
            "inserted_records": inserted_count,
            "rejected_records": rejected_count,
            "is_dry_run": dry_run,
            "rejections": rejection_reasons[:10],
        }
