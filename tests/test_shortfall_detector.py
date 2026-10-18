
from datetime import datetime
from decimal import Decimal

import pytest

from app.detection.shortfall_detector import detect_shortfall


EVALUATION_TIME = datetime.fromisoformat("2026-10-16T15:00:00+05:30")


def test_overdue_order_with_shortfall_is_actionable():
    result = detect_shortfall(
        ordered_qty=Decimal("100"),
        accepted_qty=Decimal("92"),
        expected_receipt_by=datetime.fromisoformat(
            "2026-10-15T12:00:00+05:30"
        ),
        evaluation_time=EVALUATION_TIME,
        po_status="OPEN",
    )

    assert result["actionable"] is True
    assert result["shortfall_qty"] == Decimal("8")
    assert result["reason"] == "receipt_shortfall"


def test_fully_received_order_has_no_exception():
    result = detect_shortfall(
        Decimal("40"),
        Decimal("40"),
        datetime.fromisoformat("2026-10-15T12:00:00+05:30"),
        EVALUATION_TIME,
        "OPEN",
    )

    assert result["actionable"] is False
    assert result["reason"] == "fully_received"


def test_future_deadline_is_not_actionable():
    result = detect_shortfall(
        Decimal("50"),
        Decimal("20"),
        datetime.fromisoformat("2026-10-17T18:00:00+05:30"),
        EVALUATION_TIME,
        "OPEN",
    )

    assert result["actionable"] is False
    assert result["reason"] == "receipt_deadline_not_passed"


def test_cancelled_order_is_excluded():
    result = detect_shortfall(
        Decimal("20"),
        Decimal("0"),
        datetime.fromisoformat("2026-10-15T12:00:00+05:30"),
        EVALUATION_TIME,
        "CANCELLED",
    )

    assert result["actionable"] is False
    assert result["reason"] == "purchase_order_cancelled"


def test_negative_quantity_is_rejected():
    with pytest.raises(ValueError, match="Quantities cannot be negative"):
        detect_shortfall(
            Decimal("100"),
            Decimal("-1"),
            datetime.fromisoformat("2026-10-15T12:00:00+05:30"),
            EVALUATION_TIME,
            "OPEN",
        )


def test_timezone_is_required():
    with pytest.raises(ValueError, match="must include a timezone"):
        detect_shortfall(
            Decimal("100"),
            Decimal("90"),
            datetime(2026, 10, 15, 12, 0),
            datetime(2026, 10, 16, 15, 0),
            "OPEN",
        )
