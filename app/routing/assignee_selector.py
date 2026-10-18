
from datetime import datetime


def select_assignee(
    location_id: str,
    employees: list[dict[str, str]],
    workforce_statuses: list[dict[str, str]],
    evaluation_time: datetime,
    location_aliases: list[dict[str, str]] | None = None,
) -> dict[str, str]:
    """
    Select an eligible receiving associate for a canonical store ID.
    Fall back to an eligible store manager when necessary.

    Example:
        location_id = "STORE-014"
        HRMS employee location_code = "ST-014"

    The evaluation time must be timezone-aware.
    """
    if evaluation_time.tzinfo is None:
        raise ValueError("Evaluation time must include a timezone.")

    # Map HRMS location codes to canonical store IDs.
    hrms_to_canonical: dict[str, str] = {}

    for alias in location_aliases or []:
        if alias.get("source_system", "").strip().upper() != "HRMS":
            continue

        external_id = alias.get("external_location_id", "").strip()
        canonical_id = alias.get("canonical_location_id", "").strip()

        if not external_id or not canonical_id:
            raise ValueError("Location alias IDs must not be empty.")

        existing = hrms_to_canonical.get(external_id)

        if existing is not None and existing != canonical_id:
            raise ValueError(
                f"Conflicting HRMS location alias for {external_id}: "
                f"{existing} vs {canonical_id}"
            )

        hrms_to_canonical[external_id] = canonical_id

    status_by_employee = {
        row["source_employee_id"]: row
        for row in workforce_statuses
    }

    def is_eligible(
        employee: dict[str, str],
        required_role: str,
    ) -> bool:
        employee_id = employee["source_employee_id"]
        workforce = status_by_employee.get(employee_id)

        if workforce is None:
            return False

        if employee.get("employment_status", "").strip().upper() != "ACTIVE":
            return False

        if employee.get("role", "").strip().lower() != required_role:
            return False

        if workforce.get("availability_status", "").strip().upper() != "ON_SHIFT":
            return False

        try:
            shift_start = datetime.fromisoformat(workforce["shift_start"])
            shift_end = datetime.fromisoformat(workforce["shift_end"])
        except (KeyError, ValueError):
            return False

        if shift_start.tzinfo is None or shift_end.tzinfo is None:
            return False

        if not (shift_start <= evaluation_time < shift_end):
            return False

        employee_location = employee.get("location_code", "").strip()

        # Support canonical IDs directly and HRMS aliases such as ST-014.
        employee_canonical_location = hrms_to_canonical.get(
            employee_location,
            employee_location,
        )

        return employee_canonical_location == location_id

    # Prefer an eligible receiving associate.
    associates = [
        employee
        for employee in employees
        if is_eligible(employee, "receiving_associate")
    ]

    if associates:
        selected = sorted(
            associates,
            key=lambda employee: employee["source_employee_id"],
        )[0]

        return {
            "assignee_id": selected["source_employee_id"],
            "assignee_role": selected["role"],
            "assignment_reason": "eligible_receiving_associate",
        }

    # If no associate is eligible, try an eligible store manager.
    managers = [
        employee
        for employee in employees
        if is_eligible(employee, "store_manager")
    ]

    if managers:
        selected = sorted(
            managers,
            key=lambda employee: employee["source_employee_id"],
        )[0]

        return {
            "assignee_id": selected["source_employee_id"],
            "assignee_role": selected["role"],
            "assignment_reason": "manager_fallback_no_eligible_associate",
        }

    return {
        "assignee_id": "",
        "assignee_role": "",
        "assignment_reason": "no_eligible_assignee",
    }
