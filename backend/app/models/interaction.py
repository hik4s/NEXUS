from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (
        CheckConstraint(
            "(customer_id IS NOT NULL) OR (lead_id IS NOT NULL)",
            name="ck_interactions_target",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=True
    )
    lead_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    type: Mapped[str] = mapped_column(String(40), default="note")
    channel: Mapped[str] = mapped_column(String(40), default="internal")
    subject: Mapped[str | None] = mapped_column(String(180), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company = relationship("Company")
    customer = relationship("Customer", back_populates="interactions")
    lead = relationship("Lead", back_populates="interactions")
    actor_user = relationship("User")
