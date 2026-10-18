
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExceptionRecord, TaskRecord


def persist_exception_and_task(
    db: Session,
    exception_data: dict,
    assignment: dict[str, str],
) -> tuple[ExceptionRecord, TaskRecord]:
    """
    Save an exception and its task.

    The caller controls the database transaction and should commit
    only after the surrounding ingestion operation succeeds.
    """
    required_exception_fields = {
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

    missing = required_exception_fields - exception_data.keys()
    if missing:
        raise ValueError(
            f"Missing exception fields: {', '.join(sorted(missing))}"
        )

    exception_key = str(exception_data["exception_key"]).strip()
    if not exception_key:
        raise ValueError("exception_key cannot be empty.")

    shortfall_qty = Decimal(str(exception_data["shortfall_qty"]))
    if not shortfall_qty.is_finite() or shortfall_qty <= 0:
        raise ValueError("An exception must have a positive shortfall quantity.")

    assignee_id = assignment.get("assignee_id", "").strip() or None
    assignee_role = assignment.get("assignee_role", "").strip() or None
    assignment_reason = assignment.get("assignment_reason", "").strip()

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
            po_number=str(exception_data["po_number"]).strip(),
            line_number=str(exception_data["line_number"]).strip(),
            location_id=str(exception_data["location_id"]).strip(),
            product_id=str(exception_data["product_id"]).strip(),
            ordered_qty=Decimal(str(exception_data["ordered_qty"])),
            accepted_qty=Decimal(str(exception_data["accepted_qty"])),
            shortfall_qty=shortfall_qty,
            base_uom=str(exception_data["base_uom"]).strip(),
            reason=str(exception_data["reason"]).strip(),
            status="OPEN",
        )
        db.add(exception)
        db.flush()
    else:
        # Refresh quantities for the existing exception.
        exception.ordered_qty = Decimal(str(exception_data["ordered_qty"]))
        exception.accepted_qty = Decimal(str(exception_data["accepted_qty"]))
        exception.shortfall_qty = shortfall_qty
        exception.reason = str(exception_data["reason"]).strip()

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
        # Update the current assignment without creating another task.
        task.assignee_id = assignee_id
        task.assignee_role = assignee_role
        task.assignment_reason = assignment_reason

    db.flush()
    return exception, task
