
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, ExceptionRecord, TaskRecord
from app.ingestion.exception_persistence import persist_exception_and_task


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    with TestingSession() as session:
        yield session

    engine.dispose()


def sample_exception():
    return {
        "exception_key": "SHORTFALL:PO-501:1",
        "po_number": "PO-501",
        "line_number": "1",
        "location_id": "STORE-014",
        "product_id": "SKU-001",
        "ordered_qty": Decimal("100"),
        "accepted_qty": Decimal("92"),
        "shortfall_qty": Decimal("8"),
        "base_uom": "EA",
        "reason": "receipt_shortfall",
    }


def sample_assignment():
    return {
        "assignee_id": "HR-102",
        "assignee_role": "receiving_associate",
        "assignment_reason": "eligible_receiving_associate",
    }


def test_exception_and_task_are_created(db_session):
    exception, task = persist_exception_and_task(
        db_session,
        sample_exception(),
        sample_assignment(),
    )
    db_session.commit()

    assert exception.exception_key == "SHORTFALL:PO-501:1"
    assert task.task_key == "TASK:SHORTFALL:PO-501:1"
    assert task.assignee_id == "HR-102"

    assert len(db_session.scalars(select(ExceptionRecord)).all()) == 1
    assert len(db_session.scalars(select(TaskRecord)).all()) == 1


def test_reprocessing_does_not_duplicate_exception_or_task(db_session):
    data = sample_exception()
    assignment = sample_assignment()

    first_exception, first_task = persist_exception_and_task(
        db_session, data, assignment
    )
    db_session.commit()

    second_exception, second_task = persist_exception_and_task(
        db_session, data, assignment
    )
    db_session.commit()

    assert first_exception.id == second_exception.id
    assert first_task.id == second_task.id

    assert len(db_session.scalars(select(ExceptionRecord)).all()) == 1
    assert len(db_session.scalars(select(TaskRecord)).all()) == 1


def test_existing_task_assignment_can_be_updated(db_session):
    persist_exception_and_task(
        db_session,
        sample_exception(),
        sample_assignment(),
    )
    db_session.commit()

    new_assignment = {
        "assignee_id": "HR-201",
        "assignee_role": "store_manager",
        "assignment_reason": "manager_fallback_no_eligible_associate",
    }

    exception, task = persist_exception_and_task(
        db_session,
        sample_exception(),
        new_assignment,
    )
    db_session.commit()

    assert task.assignee_id == "HR-201"
    assert task.assignment_reason == (
        "manager_fallback_no_eligible_associate"
    )
    assert len(db_session.scalars(select(ExceptionRecord)).all()) == 1
    assert len(db_session.scalars(select(TaskRecord)).all()) == 1


def test_zero_shortfall_is_rejected(db_session):
    data = sample_exception()
    data["shortfall_qty"] = Decimal("0")

    with pytest.raises(ValueError, match="positive shortfall"):
        persist_exception_and_task(
            db_session,
            data,
            sample_assignment(),
        )
