
from datetime import datetime

from app.mapping.alias_mapper import build_alias_map
from app.routing.assignee_selector import select_assignee


EVALUATION_TIME = datetime.fromisoformat(
    "2026-10-16T15:00:00+05:30"
)


def make_employee(employee_id, role, location):
    return {
        "source_employee_id": employee_id,
        "employment_status": "ACTIVE",
        "role": role,
        "location_code": location,
    }


def make_workforce(employee_id):
    return {
        "source_employee_id": employee_id,
        "availability_status": "ON_SHIFT",
        "shift_start": "2026-10-16T09:00:00+05:30",
        "shift_end": "2026-10-16T18:00:00+05:30",
    }



def test_store_014_routes_to_eligible_associate():
    location_aliases = [
        {
            "source_system": "HRMS",
            "external_location_id": "ST-014",
            "canonical_location_id": "STORE-014",
        }
    ]

    employees = [
        make_employee("HR-102", "receiving_associate", "ST-014"),
    ]
    workforce = [make_workforce("HR-102")]

    result = select_assignee(
        "STORE-014",
        employees,
        workforce,
        EVALUATION_TIME,
        location_aliases=location_aliases,
    )

    assert result["assignee_id"] == "HR-102"
    assert result["assignment_reason"] == "eligible_receiving_associate"


def test_store_015_manager_can_be_selected_as_fallback():
    location_aliases = [
        {
            "source_system": "HRMS",
            "external_location_id": "ST-015",
            "canonical_location_id": "STORE-015",
        }
    ]

    aliases = build_alias_map(
        location_aliases,
        "external_location_id",
        "canonical_location_id",
    )

    employees = [
        make_employee("HR-401", "store_manager", "ST-015"),
    ]
    workforce = [make_workforce("HR-401")]

    employee_location = next(
        external_id
        for external_id, canonical_id in aliases.items()
        if canonical_id == "STORE-015"
    )

    result = select_assignee(
        employee_location,
        employees,
        workforce,
        EVALUATION_TIME,
    )

    assert result["assignee_id"] == "HR-401"
    assert result["assignment_reason"] == (
        "manager_fallback_no_eligible_associate"
    )
