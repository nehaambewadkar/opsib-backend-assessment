
from datetime import datetime

from app.routing.assignee_selector import select_assignee


EVALUATION_TIME = datetime.fromisoformat(
    "2026-10-16T15:00:00+05:30"
)


def make_employee(employee_id, role, status="ACTIVE", location="ST-014"):
    return {
        "source_employee_id": employee_id,
        "employment_status": status,
        "role": role,
        "location_code": location,
    }


def make_workforce(employee_id, availability="ON_SHIFT"):
    return {
        "source_employee_id": employee_id,
        "availability_status": availability,
        "shift_start": "2026-10-16T09:00:00+05:30",
        "shift_end": "2026-10-16T18:00:00+05:30",
    }


def test_active_on_shift_associate_is_selected():
    employees = [
        make_employee("HR-102", "receiving_associate"),
    ]
    workforce = [make_workforce("HR-102")]

    result = select_assignee(
        "ST-014", employees, workforce, EVALUATION_TIME
    )

    assert result["assignee_id"] == "HR-102"
    assert result["assignment_reason"] == "eligible_receiving_associate"


def test_off_shift_associate_is_not_selected():
    employees = [
        make_employee("HR-101", "receiving_associate"),
    ]
    workforce = [make_workforce("HR-101", "OFF_SHIFT")]

    result = select_assignee(
        "ST-014", employees, workforce, EVALUATION_TIME
    )

    assert result["assignee_id"] == ""
    assert result["assignment_reason"] == "no_eligible_assignee"


def test_inactive_employee_is_not_selected():
    employees = [
        make_employee(
            "HR-103", "receiving_associate", status="INACTIVE"
        ),
    ]
    workforce = [make_workforce("HR-103")]

    result = select_assignee(
        "ST-014", employees, workforce, EVALUATION_TIME
    )

    assert result["assignee_id"] == ""


def test_manager_is_fallback_when_no_associate_is_eligible():
    employees = [
        make_employee(
            "HR-101",
            "receiving_associate",
        ),
        make_employee(
            "HR-201",
            "store_manager",
        ),
    ]
    workforce = [
        make_workforce("HR-101", "OFF_SHIFT"),
        make_workforce("HR-201"),
    ]

    result = select_assignee(
        "ST-014", employees, workforce, EVALUATION_TIME
    )

    assert result["assignee_id"] == "HR-201"
    assert result["assignment_reason"] == (
        "manager_fallback_no_eligible_associate"
    )


def test_employee_from_another_store_is_not_selected():
    employees = [
        make_employee(
            "HR-401",
            "store_manager",
            location="ST-015",
        ),
    ]
    workforce = [make_workforce("HR-401")]

    result = select_assignee(
        "ST-014", employees, workforce, EVALUATION_TIME
    )

    assert result["assignee_id"] == ""
