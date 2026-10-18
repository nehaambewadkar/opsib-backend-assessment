
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, PurchaseOrderLine
from app.ingestion.persistence import upsert_purchase_order_line


@pytest.fixture
def db_session():
    # Use a temporary SQLite database for isolated tests.
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


def sample_record():
    return {
        "source_record_id": "ERP-PO501-L1",
        "po_number": "PO-501",
        "line_number": "1",
        "supplier_code": "SUP-07",
        "location_id": "STORE-014",
        "product_id": "SKU-001",
        "ordered_qty": Decimal("100"),
        "base_uom": "EA",
        "status": "OPEN",
        "expected_receipt_by": datetime.fromisoformat(
            "2026-10-15T12:00:00+05:30"
        ),
    }


def test_new_purchase_order_line_is_inserted(db_session):
    record = sample_record()

    saved = upsert_purchase_order_line(db_session, record)
    db_session.commit()

    assert saved.source_record_id == "ERP-PO501-L1"

    rows = db_session.scalars(
        select(PurchaseOrderLine)
    ).all()

    assert len(rows) == 1


def test_repeated_source_record_does_not_create_duplicate(db_session):
    record = sample_record()

    first = upsert_purchase_order_line(db_session, record)
    db_session.commit()

    second = upsert_purchase_order_line(db_session, record)
    db_session.commit()

    rows = db_session.scalars(
        select(PurchaseOrderLine)
    ).all()

    assert first.id == second.id
    assert len(rows) == 1


def test_reingestion_updates_existing_record(db_session):
    record = sample_record()

    first = upsert_purchase_order_line(db_session, record)
    db_session.commit()

    updated_record = sample_record()
    updated_record["ordered_qty"] = Decimal("110")

    second = upsert_purchase_order_line(
        db_session,
        updated_record,
    )
    db_session.commit()

    assert first.id == second.id
    assert second.ordered_qty == Decimal("110")

    rows = db_session.scalars(
        select(PurchaseOrderLine)
    ).all()

    assert len(rows) == 1
