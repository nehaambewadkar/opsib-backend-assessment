
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
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
    source_record_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    po_number: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    line_number: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_code: Mapped[str] = mapped_column(String(50), nullable=False)
    location_id: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    ordered_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    base_uom: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    expected_receipt_by: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("po_number", "line_number", name="uq_po_line"),
        CheckConstraint("ordered_qty >= 0", name="ck_po_ordered_qty_nonnegative"),
    )


class ExceptionRecord(Base):
    __tablename__ = "exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exception_key: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False
    )
    po_number: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    line_number: Mapped[str] = mapped_column(String(20), nullable=False)
    location_id: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    product_id: Mapped[str] = mapped_column(String(50), nullable=False)
    ordered_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    accepted_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    shortfall_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    base_uom: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="OPEN"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped["TaskRecord | None"] = relationship(
        back_populates="exception_record",
        uselist=False,
    )

    __table_args__ = (
        CheckConstraint("ordered_qty >= 0", name="ck_exception_ordered_nonnegative"),
        CheckConstraint("accepted_qty >= 0", name="ck_exception_accepted_nonnegative"),
        CheckConstraint("shortfall_qty > 0", name="ck_exception_shortfall_positive"),
    )


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_key: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False
    )
    exception_id: Mapped[int] = mapped_column(
        ForeignKey("exceptions.id"),
        unique=True,
        nullable=False,
    )
    assignee_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    assignee_role: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    assignment_reason: Mapped[str] = mapped_column(
        String(150), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="OPEN"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    exception_record: Mapped["ExceptionRecord"] = relationship(
        back_populates="task",
    )
    audit_events: Mapped[list["TaskAuditEvent"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskAuditEvent.created_at",
    )


class TaskAuditEvent(Base):
    __tablename__ = "task_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id"), index=True, nullable=False
    )
    previous_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    new_status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped["TaskRecord"] = relationship(
        back_populates="audit_events",
    )
