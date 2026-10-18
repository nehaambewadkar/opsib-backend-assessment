
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExceptionRecord, TaskRecord


def _required_text(data: dict, field: str) -> str:
    """Return a required, non-empty string field."""
    value = data.get(field)

    if value is None:
        raise ValueError(f"{field} cannot be empty.")

    result = str(value).strip()

    if not result:
        raise ValueError(f"{field} cannot be empty.")

    return result


def _decimal_value(data: dict, field: str) -> Decimal:
    """Convert a value to a finite Decimal."""
    try:
        value = Decimal(str(data[field]))
    except (KeyError, InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a valid number.") from None

    if not value.is_finite():
        raise ValueError(f"{field} must be a finite number.")

    if value < 0:
        raise ValueError(f"{field} cannot be negative.")

    return value


def persist_exception_and_task(
    db: Session,
    exception_data: dict,
    assignment: dict[str, str],
) -> tuple[ExceptionRecord, TaskRecord]:
    """
    Persist an exception and its associated task.

    The caller controls the transaction and must commit only after
    the complete ingestion operation succeeds.

    Existing task status is preserved on repeated pipeline runs.
    Assignment changes are not automatically written to audit history
    by this function.
    """
    required_fields = {
        "exception_key",
        "po_number",
        "line_number",
        "location_id",
        "product_id",
        "ordered_qty",
        "accepted_qty",
        "shortfall_qty",
        "base_uom",
        "reason",
    }

    missing = required_fields - exception_data.keys()

    if missing:
        raise ValueError(
            f"Missing exception fields: {', '.join(sorted(missing))}"
        )

    exception_key = _required_text(exception_data, "exception_key")
    po_number = _required_text(exception_data, "po_number")
    line_number = _required_text(exception_data, "line_number")
    location_id = _required_text(exception_data, "location_id")
    product_id = _required_text(exception_data, "product_id")
    base_uom = _required_text(exception_data, "base_uom")
    reason = _required_text(exception_data, "reason")

    ordered_qty = _decimal_value(exception_data, "ordered_qty")
    accepted_qty = _decimal_value(exception_data, "accepted_qty")
    shortfall_qty = _decimal_value(exception_data, "shortfall_qty")

    if shortfall_qty <= 0:
        raise ValueError(
            "An exception must have a positive shortfall quantity."
        )

    assignee_id = (
        str(assignment.get("assignee_id") or "").strip() or None
    )
    assignee_role = (
        str(assignment.get("assignee_role") or "").strip() or None
    )
    assignment_reason = str(
        assignment.get("assignment_reason") or ""
    ).strip()

    if not assignment_reason:
        raise ValueError("assignment_reason cannot be empty.")

    exception = db.scalar(
        select(ExceptionRecord).where(
            ExceptionRecord.exception_key == exception_key
        )
    )

    if exception is None:
        exception = ExceptionRecord(
            exception_key=exception_key,
            po_number=po_number,
            line_number=line_number,
            location_id=location_id,
            product_id=product_id,
            ordered_qty=ordered_qty,
            accepted_qty=accepted_qty,
            shortfall_qty=shortfall_qty,
            base_uom=base_uom,
            reason=reason,
            status="OPEN",
        )
        db.add(exception)
        db.flush()
    else:
        # Update the existing exception without creating a duplicate.
        exception.po_number = po_number
        exception.line_number = line_number
        exception.location_id = location_id
        exception.product_id = product_id
        exception.ordered_qty = ordered_qty
        exception.accepted_qty = accepted_qty
        exception.shortfall_qty = shortfall_qty
        exception.base_uom = base_uom
        exception.reason = reason

    task_key = f"TASK:{exception_key}"

    task = db.scalar(
        select(TaskRecord).where(TaskRecord.task_key == task_key)
    )

    if task is None:
        task = TaskRecord(
            task_key=task_key,
            exception_id=exception.id,
            assignee_id=assignee_id,
            assignee_role=assignee_role,
            assignment_reason=assignment_reason,
            status="OPEN",
        )
        db.add(task)
    else:
        # Preserve the task's workflow status during ingestion reruns.
        # Do not overwrite an existing assignment if the task is
        # already being worked on or has reached a terminal state.
        if task.status == "OPEN":
            task.assignee_id = assignee_id
            task.assignee_role = assignee_role
            task.assignment_reason = assignment_reason

    db.flush()

    return exception, task
