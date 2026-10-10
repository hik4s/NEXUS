from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (UniqueConstraint("company_id", "license_number", name="uq_driver_company_license"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    license_number: Mapped[str] = mapped_column(String(40), index=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("company_id", "plate", name="uq_vehicle_company_plate"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    plate: Mapped[str] = mapped_column(String(20), index=True)
    vehicle_type: Mapped[str] = mapped_column(String(40), default="van")
    brand: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    capacity_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (UniqueConstraint("company_id", "sales_order_id", name="uq_delivery_company_sales_order"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    sales_order_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sales_orders.id", ondelete="RESTRICT"), index=True)
    warehouse_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True)
    driver_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    route_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("delivery_routes.id", ondelete="SET NULL"), nullable=True, index=True)
    tracking_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    recipient_name: Mapped[str] = mapped_column(String(160))
    recipient_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    street: Mapped[str] = mapped_column(String(180))
    number: Mapped[str] = mapped_column(String(30))
    complement: Mapped[str | None] = mapped_column(String(120), nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(80))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    proof_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    proof_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order = relationship("SalesOrder")
    warehouse = relationship("Warehouse")
    driver = relationship("Driver")
    vehicle = relationship("Vehicle")
    route = relationship("DeliveryRoute", back_populates="deliveries", foreign_keys=[route_id])
    tracking_events = relationship("TrackingEvent", back_populates="delivery", cascade="all, delete-orphan", order_by="TrackingEvent.occurred_at")


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    warehouse_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True)
    driver_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("drivers.id", ondelete="RESTRICT"), index=True)
    vehicle_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("vehicles.id", ondelete="RESTRICT"), index=True)
    route_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    route_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), default="planned", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    deliveries = relationship("Delivery", back_populates="route", foreign_keys="Delivery.route_id")
    driver = relationship("Driver")
    vehicle = relationship("Vehicle")
    warehouse = relationship("Warehouse")
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence")


class RouteStop(Base):
    __tablename__ = "route_stops"
    __table_args__ = (UniqueConstraint("route_id", "delivery_id", name="uq_route_stop_delivery"), UniqueConstraint("route_id", "sequence", name="uq_route_stop_sequence"))

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    route_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("delivery_routes.id", ondelete="CASCADE"), index=True)
    delivery_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("deliveries.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    route = relationship("DeliveryRoute", back_populates="stops")
    delivery = relationship("Delivery")


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    delivery_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("deliveries.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)

    delivery = relationship("Delivery", back_populates="tracking_events")
