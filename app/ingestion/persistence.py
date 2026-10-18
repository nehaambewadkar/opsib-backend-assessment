
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PurchaseOrderLine


def upsert_purchase_order_line(
    db: Session,
    record: dict[str, str],
) -> PurchaseOrderLine:
    """
    Insert a purchase-order line or update it when the same source
    record is ingested again.
    """
    source_record_id = record["source_record_id"].strip()

    if not source_record_id:
        raise ValueError("source_record_id cannot be empty.")

    existing = db.scalar(
        select(PurchaseOrderLine).where(
            PurchaseOrderLine.source_record_id == source_record_id
        )
    )

    values = {
        "po_number": record["po_number"].strip(),
        "line_number": record["line_number"].strip(),
        "supplier_code": record["supplier_code"].strip(),
        "location_id": record["location_id"].strip(),
        "product_id": record["product_id"].strip(),
        "ordered_qty": record["ordered_qty"],
        "base_uom": record["base_uom"].strip(),
        "status": record["status"].strip().upper(),
        "expected_receipt_by": record["expected_receipt_by"],
    }

    if existing is None:
        existing = PurchaseOrderLine(
            source_record_id=source_record_id,
            **values,
        )
        db.add(existing)
    else:
        for field, value in values.items():
            setattr(existing, field, value)

    db.flush()
    return existing
