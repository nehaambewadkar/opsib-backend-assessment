
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_record_id: Mapped[str] = mapped_column(String(100), unique=True)
    po_number: Mapped[str] = mapped_column(String(50), index=True)
    line_number: Mapped[str] = mapped_column(String(20))
    supplier_code: Mapped[str] = mapped_column(String(50))
    location_id: Mapped[str] = mapped_column(String(50), index=True)
    product_id: Mapped[str] = mapped_column(String(50), index=True)
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    base_uom: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30))
    expected_receipt_by: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "po_number",
            "line_number",
            name="uq_po_line",
        ),
    )


class ExceptionRecord(Base):
    __tablename__ = "exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exception_key: Mapped[str] = mapped_column(String(150), unique=True)
    po_number: Mapped[str] = mapped_column(String(50), index=True)
    line_number: Mapped[str] = mapped_column(String(20))
    location_id: Mapped[str] = mapped_column(String(50), index=True)
    product_id: Mapped[str] = mapped_column(String(50))
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    accepted_qty: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    shortfall_qty: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    base_uom: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    task: Mapped["TaskRecord | None"] = relationship(
        back_populates="exception_record",
        uselist=False,
    )


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_key: Mapped[str] = mapped_column(String(150), unique=True)
    exception_id: Mapped[int] = mapped_column(
        ForeignKey("exceptions.id"),
        unique=True,
    )
    assignee_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    assignee_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    assignment_reason: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    exception_record: Mapped["ExceptionRecord"] = relationship(
        back_populates="task",
    )
    audit_events: Mapped[list["TaskAuditEvent"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskAuditEvent(Base):
    __tablename__ = "task_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id"),
        index=True,
    )
    previous_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    new_status: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    task: Mapped["TaskRecord"] = relationship(
        back_populates="audit_events",
    )
