
from datetime import datetime
from decimal import Decimal


def detect_shortfall(
    ordered_qty: Decimal,
    accepted_qty: Decimal,
    expected_receipt_by: datetime,
    evaluation_time: datetime,
    po_status: str,
) -> dict:
    """Determine whether a purchase order line has an actionable shortfall."""

    if ordered_qty < 0 or accepted_qty < 0:
        raise ValueError("Quantities cannot be negative.")

    if expected_receipt_by.tzinfo is None or evaluation_time.tzinfo is None:
        raise ValueError("Receipt deadline and evaluation time must include a timezone.")

    if po_status.upper() == "CANCELLED":
        return {
            "actionable": False,
            "reason": "purchase_order_cancelled",
            "shortfall_qty": Decimal("0"),
        }

    if expected_receipt_by > evaluation_time:
        return {
            "actionable": False,
            "reason": "receipt_deadline_not_passed",
            "shortfall_qty": Decimal("0"),
        }

    shortfall_qty = max(Decimal("0"), ordered_qty - accepted_qty)

    if shortfall_qty == 0:
        return {
            "actionable": False,
            "reason": "fully_received",
            "shortfall_qty": Decimal("0"),
        }

    return {
        "actionable": True,
        "reason": "receipt_shortfall",
        "shortfall_qty": shortfall_qty,
    }
