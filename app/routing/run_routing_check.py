
import csv
from datetime import datetime
from pathlib import Path

from app.mapping.alias_mapper import build_alias_map
from app.routing.assignee_selector import select_assignee


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "fixtures"

# Frozen evaluation time from the assessment
EVALUATION_TIME = datetime.fromisoformat(
    "2026-10-16T15:00:00+05:30"
)


def read_csv(filename: str) -> list[dict[str, str]]:
    """Read a CSV fixture."""
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

        return list(reader)


def main() -> None:
    employees = read_csv("employees.csv")
    workforce_statuses = read_csv("workforce_status.csv")
    location_aliases = read_csv("location_aliases.csv")

    # Validate the HRMS location aliases.
    hrms_aliases = [
        row
        for row in location_aliases
        if row["source_system"].strip().upper() == "HRMS"
    ]

    build_alias_map(
        hrms_aliases,
        "external_location_id",
        "canonical_location_id",
    )

    # Check each store using its canonical ID.
    for store_id in ("STORE-014", "STORE-015"):
        result = select_assignee(
            location_id=store_id,
            employees=employees,
            workforce_statuses=workforce_statuses,
            evaluation_time=EVALUATION_TIME,
            location_aliases=hrms_aliases,
        )

        print(
            f"{store_id}: "
            f"assignee={result['assignee_id'] or 'NONE'}, "
            f"role={result['assignee_role'] or 'NONE'}, "
            f"reason={result['assignment_reason']}"
        )


if __name__ == "__main__":
    main()
