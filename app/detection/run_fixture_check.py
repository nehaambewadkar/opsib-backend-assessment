
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.detection.shortfall_detector import detect_shortfall
from app.ingestion.csv_loader import deduplicate_by_source_id
from app.mapping.alias_mapper import build_product_alias_map


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "fixtures"

# Frozen evaluation time required by the assessment
EVALUATION_TIME = datetime.fromisoformat(
    "2026-10-16T15:00:00+05:30"
)


def read_csv(filename: str) -> list[dict[str, str]]:
    """Read a CSV fixture from the fixtures directory."""
    file_path = FIXTURES / filename

    if not file_path.is_file():
        raise FileNotFoundError(f"Fixture not found: {file_path}")

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {filename}")

        if any(not name.strip() for name in reader.fieldnames):
            raise ValueError(f"CSV has an empty column name: {filename}")

        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"CSV has duplicate column names: {filename}")

        rows = list(reader)

        if any(None in row for row in rows):
            raise ValueError(f"CSV has a row with extra columns: {filename}")

        if any(
            value is None
            for row in rows
            for value in row.values()
        ):
            raise ValueError(f"CSV has a row with missing values: {filename}")

        return rows


def load_unique_records(
    filename: str,
) -> list[dict[str, str]]:
    """Remove identical repeated source records and reject conflicts."""
    rows = read_csv(filename)
    unique_rows, conflicts = deduplicate_by_source_id(rows)

    if conflicts:
        raise ValueError(
            f"Conflicting records found in {filename}: {conflicts}"
        )

    return unique_rows


def main() -> None:
    # Load purchase orders and receipts, deduplicating by source_record_id.
    purchase_orders = load_unique_records("purchase_order_lines.csv")
    receipts = load_unique_records("goods_receipt_lines.csv")

    # Load product aliases and unit-conversion factors.
    product_aliases = build_product_alias_map(
        read_csv("product_aliases.csv")
    )

    # Key receipts by (PO number, PO line number).
    accepted_by_po_line: dict[tuple[str, str], Decimal] = {}

    for receipt in receipts:
        # Only posted receipts count toward accepted quantity.
        if receipt["posting_status"].strip().upper() != "POSTED":
            continue

        product_key = (
            "WMS",
            receipt["product_ref"].strip(),
        )

        alias = product_aliases.get(product_key)

        if alias is None:
            raise ValueError(
                f"Unknown WMS product: {receipt['product_ref']}"
            )

        receipt_uom = receipt["uom"].strip()

        if receipt_uom != alias["source_uom"]:
            raise ValueError(
                f"Unexpected receipt unit {receipt_uom!r} for "
                f"{receipt['source_record_id']}; "
                f"expected {alias['source_uom']!r}"
            )

        accepted_qty = Decimal(receipt["accepted_qty"])

        if not accepted_qty.is_finite() or accepted_qty < 0:
            raise ValueError(
                f"Invalid accepted quantity in "
                f"{receipt['source_record_id']}"
            )

        # Convert receipt quantity into the product's base unit.
        base_qty = accepted_qty * Decimal(alias["to_base_factor"])

        po_line_key = (
            receipt["po_number"].strip(),
            receipt["po_line_number"].strip(),
        )

        accepted_by_po_line[po_line_key] = (
            accepted_by_po_line.get(po_line_key, Decimal("0"))
            + base_qty
        )

    print(f"Frozen evaluation time: {EVALUATION_TIME.isoformat()}")
    print(f"Unique purchase-order lines: {len(purchase_orders)}")
    print(f"Unique receipt records: {len(receipts)}")
    print("-" * 90)

    # Evaluate each purchase-order line independently.
    for po in purchase_orders:
        po_number = po["po_number"].strip()
        line_number = po["line_number"].strip()

        product_key = (
            "ERP",
            po["item_code"].strip(),
        )

        alias = product_aliases.get(product_key)

        if alias is None:
            raise ValueError(
                f"Unknown ERP product: {po['item_code']}"
            )

        ordered_uom = po["ordered_uom"].strip()

        if ordered_uom != alias["source_uom"]:
            raise ValueError(
                f"Unexpected order unit {ordered_uom!r} for "
                f"{po['source_record_id']}; "
                f"expected {alias['source_uom']!r}"
            )

        ordered_qty = Decimal(po["ordered_qty"])

        if not ordered_qty.is_finite() or ordered_qty < 0:
            raise ValueError(
                f"Invalid ordered quantity in {po['source_record_id']}"
            )

        # Convert the ordered quantity into the same base unit as receipts.
        ordered_base_qty = (
            ordered_qty * Decimal(alias["to_base_factor"])
        )

        po_line_key = (po_number, line_number)

        accepted_base_qty = accepted_by_po_line.get(
            po_line_key,
            Decimal("0"),
        )

        result = detect_shortfall(
            ordered_qty=ordered_base_qty,
            accepted_qty=accepted_base_qty,
            expected_receipt_by=datetime.fromisoformat(
                po["expected_receipt_by"]
            ),
            evaluation_time=EVALUATION_TIME,
            po_status=po["status"],
        )

        print(
            f"{po_number} line {line_number}: "
            f"ordered={ordered_base_qty} {alias['base_uom']}, "
            f"accepted={accepted_base_qty} {alias['base_uom']}, "
            f"actionable={result['actionable']}, "
            f"shortfall={result['shortfall_qty']} {alias['base_uom']}, "
            f"reason={result['reason']}"
        )


if __name__ == "__main__":
    main()
