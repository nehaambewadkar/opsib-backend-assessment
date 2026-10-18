
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TaskRecord, TaskAuditEvent


# Allowed task status transitions.
ALLOWED_TRANSITIONS = {
    "OPEN": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"RESOLVED", "CANCELLED", "OPEN"},
    "RESOLVED": set(),
    "CANCELLED": set(),
}


def transition_task_status(
    db: Session,
    task_id: int,
    new_status: str,
    actor_id: str,
    reason: str,
) -> TaskRecord:
    """
    Change a task's status and record the change in the audit history.

    The caller controls the database transaction and must commit or roll back.
    """

    # Validate the request.
    new_status = new_status.strip().upper()

    if new_status not in ALLOWED_TRANSITIONS:
        raise ValueError(f"Invalid task status: {new_status}")

    if not actor_id or not actor_id.strip():
        raise ValueError("actor_id is required.")

    if not reason or not reason.strip():
        raise ValueError("A reason is required for a status change.")

    # Lock the task row to reduce concurrent status-change conflicts.
    task = db.execute(
        select(TaskRecord)
        .where(TaskRecord.id == task_id)
        .with_for_update()
    ).scalar_one_or_none()

    if task is None:
        raise ValueError(f"Task {task_id} was not found.")

    previous_status = task.status.upper()

    # Prevent invalid or repeated transitions.
    allowed = ALLOWED_TRANSITIONS.get(previous_status, set())

    if new_status not in allowed:
        raise ValueError(
            f"Cannot change task status from "
            f"{previous_status} to {new_status}."
        )

    # Update the task.
    task.status = new_status

    # Record who changed it, what changed, and why.
    audit_event = TaskAuditEvent(
        task_id=task.id,
        previous_status=previous_status,
        new_status=new_status,
        actor_id=actor_id.strip(),
        reason=reason.strip(),
    )

    db.add(audit_event)

    # Send pending changes to the database without committing.
    db.flush()

    return task
