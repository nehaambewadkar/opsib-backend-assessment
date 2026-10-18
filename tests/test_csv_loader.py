
from pathlib import Path

from app.ingestion.csv_loader import load_csv


def test_load_csv_returns_rows_as_dictionaries(tmp_path: Path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(
        "id,quantity\nPO-501,100\nPO-502,40\n",
        encoding="utf-8",
    )

    rows = load_csv(csv_file)

    assert len(rows) == 2
    assert rows[0]["id"] == "PO-501"
    assert rows[0]["quantity"] == "100"


def test_load_csv_missing_file_raises_error(tmp_path: Path):
    missing_file = tmp_path / "missing.csv"

    try:
        load_csv(missing_file)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass
    
from app.ingestion.csv_loader import deduplicate_rows


def test_deduplicate_rows_removes_exact_duplicates():
    rows = [
        {"po_number": "PO-501", "quantity": "10"},
        {"po_number": "PO-501", "quantity": "10"},
        {"po_number": "PO-502", "quantity": "20"},
    ]

    result = deduplicate_rows(rows)

    assert len(result) == 2
    assert result[0]["po_number"] == "PO-501"
    assert result[1]["po_number"] == "PO-502"


from app.ingestion.csv_loader import deduplicate_by_source_id


def test_deduplicate_by_source_id_removes_identical_duplicates():
    rows = [
        {"source_record_id": "PO-1", "quantity": "10"},
        {"source_record_id": "PO-1", "quantity": "10"},
    ]

    unique_rows, conflicts = deduplicate_by_source_id(rows)

    assert len(unique_rows) == 1
    assert conflicts == []


def test_deduplicate_by_source_id_flags_conflicting_records():
    rows = [
        {"source_record_id": "PO-1", "quantity": "10"},
        {"source_record_id": "PO-1", "quantity": "20"},
    ]

    unique_rows, conflicts = deduplicate_by_source_id(rows)

    assert len(unique_rows) == 1
    assert len(conflicts) == 1
    assert conflicts[0]["reason"] == "conflicting_source_record_id"
