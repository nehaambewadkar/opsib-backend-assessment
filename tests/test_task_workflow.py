
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.db.models import TaskRecord, TaskAuditEvent
from app.workflows.task_workflow import transition_task_status


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def task(db):
    task = TaskRecord(
        task_key="TASK:TEST-001",
        exception_id=1,
        assignee_id="HR-102",
        assignee_role="receiving_associate",
        assignment_reason="eligible_receiving_associate",
        status="OPEN",
    )

    db.add(task)
    db.flush()

    return task


def test_valid_status_transition_creates_audit_event(db, task):
    updated_task = transition_task_status(
        db=db,
        task_id=task.id,
        new_status="IN_PROGRESS",
        actor_id="HR-102",
        reason="Started investigating the receipt shortfall.",
    )

    db.flush()

    assert updated_task.status == "IN_PROGRESS"

    event = db.execute(
        select(TaskAuditEvent).where(
            TaskAuditEvent.task_id == task.id
        )
    ).scalar_one()

    assert event.previous_status == "OPEN"
    assert event.new_status == "IN_PROGRESS"
    assert event.actor_id == "HR-102"
    assert event.reason == "Started investigating the receipt shortfall."


def test_invalid_transition_is_rejected(db, task):
    with pytest.raises(ValueError, match="Cannot change task status"):
        transition_task_status(
            db=db,
            task_id=task.id,
            new_status="RESOLVED",
            actor_id="HR-102",
            reason="Trying to resolve without starting.",
        )

    assert task.status == "OPEN"

    events = db.execute(
        select(TaskAuditEvent).where(
            TaskAuditEvent.task_id == task.id
        )
    ).scalars().all()

    assert len(events) == 0


def test_missing_task_is_rejected(db):
    with pytest.raises(ValueError, match="was not found"):
        transition_task_status(
            db=db,
            task_id=9999,
            new_status="IN_PROGRESS",
            actor_id="HR-102",
            reason="Test missing task.",
        )


@pytest.mark.parametrize(
    ("actor_id", "reason"),
    [
        ("", "Valid reason"),
        ("HR-102", ""),
    ],
)
def test_actor_and_reason_are_required(db, task, actor_id, reason):
    with pytest.raises(ValueError):
        transition_task_status(
            db=db,
            task_id=task.id,
            new_status="IN_PROGRESS",
            actor_id=actor_id,
            reason=reason,
        )

    assert task.status == "OPEN"
