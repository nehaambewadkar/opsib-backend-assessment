
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.db.session import SessionLocal
from app.detection.shortfall_detector import detect_shortfall
from app.ingestion.csv_loader import (
    load_csv,
    validate_columns,
    deduplicate_by_source_id,
)
from app.ingestion.persistence import upsert_purchase_order_line
from app.ingestion.exception_persistence import persist_exception_and_task
from app.mapping.alias_mapper import (
    build_alias_map,
    build_product_alias_map,
)
from app.routing.assignee_selector import select_assignee


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "fixtures"

EVALUATION_TIME = datetime.fromisoformat(
    "2026-10-16T15:00:00+05:30"
)


def load_unique_csv(filename, required_columns):
    """Load and validate a CSV, deduplicating source records when available."""
    rows = load_csv(FIXTURES_DIR / filename)
    validate_columns(rows, set(required_columns))

    if rows and "source_record_id" not in rows[0]:
        return rows

    unique_rows, conflicts = deduplicate_by_source_id(rows)

    if conflicts:
        raise ValueError(
            f"Conflicting duplicate records in {filename}: {conflicts}"
        )

    return unique_rows


def run_pipeline():
    purchase_orders = load_unique_csv(
        "purchase_order_lines.csv",
        [
            "source_record_id", "po_number", "line_number",
            "supplier_code", "location_code", "item_code",
            "ordered_qty", "ordered_uom", "status",
            "expected_receipt_by",
        ],
    )

    receipts = load_unique_csv(
        "goods_receipt_lines.csv",
        [
            "source_record_id", "po_number", "po_line_number",
            "location_code", "product_ref", "accepted_qty",
            "uom", "received_at", "posting_status",
        ],
    )

    product_aliases = load_unique_csv(
        "product_aliases.csv",
        [
            "source_system", "external_item_id",
            "canonical_product_id", "source_uom",
            "base_uom", "to_base_factor",
        ],
    )

    location_aliases = load_unique_csv(
        "location_aliases.csv",
        [
            "source_system", "external_location_id",
            "canonical_location_id",
        ],
    )

    employees = load_csv(FIXTURES_DIR / "employees.csv")
    workforce_statuses = load_csv(
        FIXTURES_DIR / "workforce_status.csv"
    )

    product_map = build_product_alias_map(product_aliases)

    location_map = build_alias_map(
        location_aliases,
        source_id_column="external_location_id",
        canonical_id_column="canonical_location_id",
    )

    # Aggregate only posted receipts, converting quantities to base units.
    accepted_by_line = {}

    for receipt in receipts:
        if receipt["posting_status"].strip().upper() != "POSTED":
            continue

        alias_key = ("WMS", receipt["product_ref"].strip())
        alias = product_map.get(alias_key)

        if alias is None:
            raise ValueError(
                f"Missing product alias for receipt "
                f"{receipt['source_record_id']}"
            )

        quantity = (
            Decimal(receipt["accepted_qty"])
            * Decimal(alias["to_base_factor"])
        )

        key = (
            receipt["po_number"].strip(),
            str(receipt["po_line_number"]).strip(),
        )

        accepted_by_line[key] = (
            accepted_by_line.get(key, Decimal("0")) + quantity
        )

    db = SessionLocal()

    try:
        actionable_count = 0

        for po in purchase_orders:
            po_number = po["po_number"].strip()
            line_number = str(po["line_number"]).strip()
            key = (po_number, line_number)

            product_alias = product_map.get(
                ("ERP", po["item_code"].strip())
            )

            if product_alias is None:
                raise ValueError(
                    f"Missing product alias for PO line {key}"
                )

            location_id = location_map.get(
                po["location_code"].strip()
            )

            if location_id is None:
                raise ValueError(
                    f"Missing location alias for "
                    f"{po['location_code']}"
                )

            ordered_qty = (
                Decimal(po["ordered_qty"])
                * Decimal(product_alias["to_base_factor"])
            )
            accepted_qty = accepted_by_line.get(
                key, Decimal("0")
            )
            base_uom = product_alias["base_uom"]

            # Persist the purchase-order line.
            po_record = {
                "source_record_id": po["source_record_id"],
                "po_number": po_number,
                "line_number": line_number,
                "supplier_code": po["supplier_code"],
                "location_id": location_id,
                "product_id": product_alias["canonical_product_id"],
                "ordered_qty": ordered_qty,
                "base_uom": base_uom,
                "status": po["status"].strip().upper(),
                "expected_receipt_by": datetime.fromisoformat(
                    po["expected_receipt_by"].strip()
                ),
            }

            upsert_purchase_order_line(db, po_record)

            result = detect_shortfall(
                ordered_qty=ordered_qty,
                accepted_qty=accepted_qty,
                expected_receipt_by=po_record["expected_receipt_by"],
                evaluation_time=EVALUATION_TIME,
                po_status=po_record["status"],
            )

            print(
                f"{po_number} line {line_number}: "
                f"ordered={ordered_qty} {base_uom}, "
                f"accepted={accepted_qty} {base_uom}, "
                f"actionable={result['actionable']}, "
                f"reason={result['reason']}"
            )

            if not result["actionable"]:
                continue

            assignment = select_assignee(
                location_id=location_id,
                employees=employees,
                workforce_statuses=workforce_statuses,
                evaluation_time=EVALUATION_TIME,
                location_aliases=location_aliases,
            )

            exception_key = (
                f"{po_number}:{line_number}:receipt_shortfall"
            )

            exception_data = {
                "exception_key": exception_key,
                "po_number": po_number,
                "line_number": line_number,
                "location_id": location_id,
                "product_id": product_alias["canonical_product_id"],
                "ordered_qty": ordered_qty,
                "accepted_qty": accepted_qty,
                "shortfall_qty": result["shortfall_qty"],
                "base_uom": base_uom,
                "reason": result["reason"],
            }

            exception, task = persist_exception_and_task(
                db,
                exception_data,
                assignment,
            )

            actionable_count += 1

            print(
                f"  Saved exception #{exception.id}; "
                f"task #{task.id}; "
                f"assignee={assignment.get('assignee_id')}; "
                f"assignment_reason="
                f"{assignment.get('assignment_reason')}"
            )

        # Commit the complete pipeline as one transaction.
        db.commit()

        print("-" * 70)
        print("Pipeline completed successfully.")
        print(f"Actionable exceptions processed: {actionable_count}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print(f"Evaluation time: {EVALUATION_TIME.isoformat()}")
    run_pipeline()
