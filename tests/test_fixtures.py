
from pathlib import Path

from app.ingestion.csv_loader import load_csv


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

EXPECTED_COLUMNS = {
    "purchase_order_lines.csv": {
        "po_number", "line_number", "ordered_qty",
        "ordered_uom", "expected_receipt_by",
    },
    "goods_receipt_lines.csv": {
        "po_number", "po_line_number", "accepted_qty",
        "uom", "received_at", "posting_status",
    },
    "product_aliases.csv": {
        "source_system", "external_item_id",
        "canonical_product_id", "source_uom",
        "base_uom", "to_base_factor",
    },
    "location_aliases.csv": {
        "source_system", "external_location_id",
        "canonical_location_id", "region_id",
    },
    "employees.csv": {
        "source_employee_id", "employment_status",
        "role", "location_code", "region_id",
    },
    "workforce_status.csv": {
        "source_employee_id", "availability_status",
        "shift_start", "shift_end", "observed_at",
    },
}


def test_all_fixture_files_have_expected_columns():
    for filename, required_columns in EXPECTED_COLUMNS.items():
        rows = load_csv(FIXTURES / filename)

        assert rows, f"{filename} has no data rows"
        assert required_columns.issubset(rows[0].keys()), (
            f"{filename} is missing columns: "
            f"{required_columns - rows[0].keys()}"
        )
