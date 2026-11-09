from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OrderImportBatch(Base):
    __tablename__ = 'order_import_batches'
    __table_args__ = (
        UniqueConstraint('company_id', 'sha256', name='uq_order_import_company_hash'),
        CheckConstraint("status IN ('reviewed','committed','partially_committed')", name='ck_order_import_batch_status'),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey('companies.id', ondelete='CASCADE'), index=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    filename: Mapped[str] = mapped_column(String(120))
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default='reviewed')
    unassigned_errors: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    entries: Mapped[list['OrderImportEntry']] = relationship(back_populates='batch', cascade='all, delete-orphan', order_by='OrderImportEntry.position')


class OrderImportEntry(Base):
    __tablename__ = 'order_import_entries'
    __table_args__ = (
        UniqueConstraint('batch_id', 'external_order_id', name='uq_order_import_batch_external'),
        CheckConstraint("status IN ('valid','invalid','committed','duplicate')", name='ck_order_import_entry_status'),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey('order_import_batches.id', ondelete='CASCADE'), index=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey('companies.id', ondelete='CASCADE'), index=True)
    external_order_id: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column()
    source_lines: Mapped[list] = mapped_column(JSON)
    normalized_items: Mapped[list] = mapped_column(JSON)
    parser_errors: Mapped[list] = mapped_column(JSON, default=list)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16))
    sales_order_id: Mapped[UUID | None] = mapped_column(ForeignKey('sales_orders.id', ondelete='RESTRICT'), nullable=True)
    batch: Mapped[OrderImportBatch] = relationship(back_populates='entries')


class OrderImportSource(Base):
    __tablename__ = 'order_import_sources'
    __table_args__ = (
        UniqueConstraint('company_id', 'external_order_id', name='uq_order_import_source_external'),
        UniqueConstraint('sales_order_id', name='uq_order_import_source_order'),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey('companies.id', ondelete='CASCADE'), index=True)
    external_order_id: Mapped[str] = mapped_column(String(80))
    sales_order_id: Mapped[UUID] = mapped_column(ForeignKey('sales_orders.id', ondelete='RESTRICT'))
