
import csv
from pathlib import Path


def load_csv(file_path: str | Path) -> list[dict[str, str]]:
    """Load a CSV file and validate its headers."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")

        if any(not name.strip() for name in reader.fieldnames):
            raise ValueError(f"CSV has an empty column name: {path}")

        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"CSV has duplicate column names: {path}")

        rows = list(reader)

        if any(None in row for row in rows):
            raise ValueError(f"CSV contains a row with extra columns: {path}")

        if any(value is None for row in rows for value in row.values()):
            raise ValueError(f"CSV contains a row with missing values: {path}")

        return rows


def validate_columns(
    rows: list[dict[str, str]],
    required_columns: set[str],
) -> None:
    """Ensure the CSV contains data and all required columns."""
    if not rows:
        raise ValueError("CSV contains no data rows.")

    actual_columns = set(rows[0].keys())
    missing = required_columns - actual_columns

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing))}"
        )


def deduplicate_by_source_id(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Deduplicate identical records by source_record_id.

    Returns:
        (unique_rows, conflicts)

    Repeated IDs with different content are reported as conflicts.
    They are not silently accepted as valid records.
    """
    unique_by_id: dict[str, dict[str, str]] = {}
    conflicts: list[dict[str, str]] = []

    for row in rows:
        source_id = row.get("source_record_id", "").strip()

        if not source_id:
            conflicts.append({
                "reason": "missing_source_record_id",
                "row": repr(row),
            })
            continue

        existing = unique_by_id.get(source_id)

        if existing is None:
            unique_by_id[source_id] = row.copy()
        elif existing != row:
            conflicts.append({
                "reason": "conflicting_source_record_id",
                "source_record_id": source_id,
                "first_record": repr(existing),
                "conflicting_record": repr(row),
            })
        # Identical records with the same ID are safely ignored.

    return list(unique_by_id.values()), conflicts

def deduplicate_rows(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Backward-compatible helper for exact duplicate rows."""
    unique_rows = []
    seen = set()

    for row in rows:
        fingerprint = tuple(sorted(row.items()))

        if fingerprint not in seen:
            seen.add(fingerprint)
            unique_rows.append(row)

    return unique_rows
