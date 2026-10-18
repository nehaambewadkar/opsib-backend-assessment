
import csv
from pathlib import Path


def load_csv(file_path: str | Path) -> list[dict[str, str]]:
    """Load a CSV file and validate its headers and rows."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")

        # Normalize header whitespace.
        headers = [name.strip() for name in reader.fieldnames]

        if any(not name for name in headers):
            raise ValueError(f"CSV has an empty column name: {path}")

        # Reject duplicate names, including names duplicated after trimming.
        if len(headers) != len(set(headers)):
            raise ValueError(
                f"CSV has duplicate column names after trimming: {path}"
            )

        reader.fieldnames = headers
        rows = list(reader)

        # Reject rows containing more values than the header.
        if any(None in row for row in rows):
            raise ValueError(f"CSV contains a row with extra columns: {path}")

        # Reject rows with fewer values than the header.
        if any(
            value is None
            for row in rows
            for value in row.values()
        ):
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
    Deduplicate records by source_record_id.

    Returns:
        (unique_rows, conflicts)

    Identical records with the same source ID are counted once.
    Records with missing IDs or conflicting content are reported
    in conflicts and are not silently accepted.
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

        # Normalize the ID in the record used for comparison.
        normalized_row = row.copy()
        normalized_row["source_record_id"] = source_id

        existing = unique_by_id.get(source_id)

        if existing is None:
            unique_by_id[source_id] = normalized_row

        elif existing != normalized_row:
            conflicts.append({
                "reason": "conflicting_source_record_id",
                "source_record_id": source_id,
                "first_record": repr(existing),
                "conflicting_record": repr(normalized_row),
            })

        # Exact repeated records with the same ID are safely ignored.

    return list(unique_by_id.values()), conflicts


def deduplicate_rows(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Remove exact duplicate rows while preserving their original order."""
    unique_rows: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()

    for row in rows:
        fingerprint = tuple(sorted(row.items()))

        if fingerprint not in seen:
            seen.add(fingerprint)
            unique_rows.append(row)

    return unique_rows
