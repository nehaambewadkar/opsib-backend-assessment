
from pathlib import Path

from app.ingestion.csv_loader import load_csv, deduplicate_rows


FIXTURES = Path(__file__).resolve().parent / "fixtures"

FILES_TO_CHECK = [
    "purchase_order_lines.csv",
    "goods_receipt_lines.csv",
    "product_aliases.csv",
    "location_aliases.csv",
    "employees.csv",
    "workforce_status.csv",
]


for filename in FILES_TO_CHECK:
    rows = load_csv(FIXTURES / filename)
    unique_rows = deduplicate_rows(rows)

    print(f"\n{filename}")
    print(f"  Rows before deduplication: {len(rows)}")
    print(f"  Rows after deduplication:  {len(unique_rows)}")
    print(f"  Exact duplicates removed:  {len(rows) - len(unique_rows)}")
