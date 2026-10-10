from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import record_audit
from app.models.inventory import Warehouse
from app.models.logistics import Delivery, DeliveryRoute, Driver, RouteStop, TrackingEvent, Vehicle
from app.models.order import SalesOrder
from app.models.user import User
from app.rbac.service import user_has_permission
from app.schemas.logistics import DeliveryAssign, DeliveryCreate, DeliveryStatusUpdate, DriverCreate, RouteCreate, RouteStopCreate, VehicleCreate

DELIVERY_TRANSITIONS = {
    "pending": {"assigned", "cancelled"},
    "assigned": {"in_transit", "cancelled"},
    "in_transit": {"delivered", "failed"},
    "failed": {"assigned", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}


def _warehouse(db: Session, company_id: UUID, warehouse_id: UUID) -> Warehouse:
    item = db.scalar(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.company_id == company_id, Warehouse.is_active.is_(True)))
    if item is None:
        raise HTTPException(status_code=404, detail="Warehouse not found or inactive")
    return item


def _driver(db: Session, company_id: UUID, driver_id: UUID) -> Driver:
    item = db.scalar(select(Driver).where(Driver.id == driver_id, Driver.company_id == company_id, Driver.is_active.is_(True)))
    if item is None:
        raise HTTPException(status_code=404, detail="Driver not found or inactive")
    return item


def _vehicle(db: Session, company_id: UUID, vehicle_id: UUID) -> Vehicle:
    item = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.company_id == company_id, Vehicle.is_active.is_(True)))
    if item is None:
        raise HTTPException(status_code=404, detail="Vehicle not found or inactive")
    return item


def create_driver(db: Session, actor: User, payload: DriverCreate, request=None) -> Driver:
    if payload.user_id is not None:
        user = db.scalar(select(User).where(User.id == payload.user_id, User.company_id == actor.company_id, User.is_active.is_(True)))
        if user is None:
            raise HTTPException(status_code=404, detail="Driver user not found or inactive")
    if db.scalar(select(Driver).where(Driver.company_id == actor.company_id, Driver.license_number == payload.license_number)):
        raise HTTPException(status_code=409, detail="Driver license already registered")
    item = Driver(company_id=actor.company_id, user_id=payload.user_id, full_name=payload.full_name, phone=payload.phone, license_number=payload.license_number)
    db.add(item); db.flush()
    record_audit(db, request=request, action="driver.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="driver", resource_id=item.id, metadata={"license_number": item.license_number})
    db.commit(); db.refresh(item)
    return item


def list_drivers(db: Session, company_id: UUID) -> list[Driver]:
    return list(db.scalars(select(Driver).where(Driver.company_id == company_id).order_by(Driver.full_name)).all())


def create_vehicle(db: Session, actor: User, payload: VehicleCreate, request=None) -> Vehicle:
    if db.scalar(select(Vehicle).where(Vehicle.company_id == actor.company_id, Vehicle.plate == payload.plate.upper())):
        raise HTTPException(status_code=409, detail="Vehicle plate already registered")
    item = Vehicle(company_id=actor.company_id, plate=payload.plate.upper(), vehicle_type=payload.vehicle_type, brand=payload.brand, model=payload.model, capacity_kg=payload.capacity_kg)
    db.add(item); db.flush()
    record_audit(db, request=request, action="vehicle.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="vehicle", resource_id=item.id, metadata={"plate": item.plate})
    db.commit(); db.refresh(item)
    return item


def list_vehicles(db: Session, company_id: UUID) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).where(Vehicle.company_id == company_id).order_by(Vehicle.plate)).all())


def _get_order(db: Session, company_id: UUID, order_id: UUID) -> SalesOrder:
    order = db.scalar(select(SalesOrder).options(selectinload(SalesOrder.fulfillment)).where(SalesOrder.id == order_id, SalesOrder.company_id == company_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return order


def _get_delivery(db: Session, company_id: UUID, delivery_id: UUID) -> Delivery:
    item = db.scalar(select(Delivery).where(Delivery.id == delivery_id, Delivery.company_id == company_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return item


def create_delivery(db: Session, actor: User, payload: DeliveryCreate, request=None) -> Delivery:
    order = _get_order(db, actor.company_id, payload.sales_order_id)
    if order.status != "confirmed":
        raise HTTPException(status_code=409, detail="Delivery can only be created for a confirmed sales order")
    if order.fulfillment is None:
        raise HTTPException(status_code=409, detail="Sales order has no warehouse fulfillment")
    existing = db.scalar(select(Delivery).where(Delivery.company_id == actor.company_id, Delivery.sales_order_id == order.id))
    if existing:
        raise HTTPException(status_code=409, detail="A delivery already exists for this sales order")
    _warehouse(db, actor.company_id, order.fulfillment.warehouse_id)
    item = Delivery(company_id=actor.company_id, sales_order_id=order.id, warehouse_id=order.fulfillment.warehouse_id, tracking_code=f"NX-{uuid4().hex[:14].upper()}", recipient_name=payload.recipient_name, recipient_phone=payload.recipient_phone, postal_code=payload.postal_code, street=payload.street, number=payload.number, complement=payload.complement, neighborhood=payload.neighborhood, city=payload.city, state=payload.state, scheduled_at=payload.scheduled_at)
    db.add(item); db.flush()
    _track(db, actor, item, "pending", "Delivery created")
    record_audit(db, request=request, action="delivery.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="delivery", resource_id=item.id, metadata={"tracking_code": item.tracking_code, "sales_order_id": str(order.id)})
    db.commit(); return get_delivery(db, actor.company_id, item.id)


def list_deliveries(db: Session, company_id: UUID, status_filter: str | None = None) -> list[Delivery]:
    stmt = select(Delivery).where(Delivery.company_id == company_id).order_by(Delivery.created_at.desc())
    if status_filter: stmt = stmt.where(Delivery.status == status_filter)
    return list(db.scalars(stmt).all())


def get_delivery(db: Session, company_id: UUID, delivery_id: UUID) -> Delivery:
    item = db.scalar(select(Delivery).where(Delivery.id == delivery_id, Delivery.company_id == company_id))
    if item is None: raise HTTPException(status_code=404, detail="Delivery not found")
    return item


def assign_delivery(db: Session, actor: User, delivery: Delivery, payload: DeliveryAssign, request=None) -> Delivery:
    if delivery.status not in {"pending", "failed"}:
        raise HTTPException(status_code=409, detail="Only pending or failed deliveries can be assigned")
    driver = _driver(db, actor.company_id, payload.driver_id)
    _vehicle(db, actor.company_id, payload.vehicle_id)
    route_conflict = db.scalar(select(Delivery).where(Delivery.company_id == actor.company_id, Delivery.driver_id == driver.id, Delivery.status.in_(["assigned", "in_transit"]), Delivery.id != delivery.id))
    if route_conflict:
        raise HTTPException(status_code=409, detail="Driver already has an active delivery")
    delivery.driver_id = driver.id; delivery.vehicle_id = payload.vehicle_id; delivery.status = "assigned"
    db.flush(); _track(db, actor, delivery, "assigned", "Driver and vehicle assigned")
    record_audit(db, request=request, action="delivery.assigned", company_id=actor.company_id, actor_user_id=actor.id, resource_type="delivery", resource_id=delivery.id, metadata={"driver_id": str(driver.id), "vehicle_id": str(payload.vehicle_id)})
    db.commit(); return get_delivery(db, actor.company_id, delivery.id)


def update_delivery_status(db: Session, actor: User, delivery: Delivery, payload: DeliveryStatusUpdate, request=None) -> Delivery:
    if payload.status not in DELIVERY_TRANSITIONS.get(delivery.status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot transition delivery from {delivery.status} to {payload.status}")
    now = datetime.now(timezone.utc)
    if payload.status == "in_transit":
        if delivery.driver_id is None or delivery.vehicle_id is None:
            raise HTTPException(status_code=409, detail="Delivery must have driver and vehicle before dispatch")
        delivery.dispatched_at = now
    if payload.status == "delivered":
        if not payload.proof_type or not payload.proof_reference:
            raise HTTPException(status_code=422, detail="proof_type and proof_reference are required when delivering")
        delivery.delivered_at = now; delivery.proof_type = payload.proof_type; delivery.proof_reference = payload.proof_reference; delivery.failure_reason = None
    if payload.status == "failed":
        if not payload.failure_reason: raise HTTPException(status_code=422, detail="failure_reason is required when delivery fails")
        delivery.failure_reason = payload.failure_reason
    if payload.status == "cancelled":
        delivery.failure_reason = payload.failure_reason
    delivery.status = payload.status
    db.flush(); _track(db, actor, delivery, payload.status, payload.description, payload.latitude, payload.longitude)
    record_audit(db, request=request, action="delivery.status_changed", company_id=actor.company_id, actor_user_id=actor.id, resource_type="delivery", resource_id=delivery.id, metadata={"status": payload.status})
    db.commit(); return get_delivery(db, actor.company_id, delivery.id)


def _track(db: Session, actor: User, delivery: Delivery, event_status: str, description: str | None = None, latitude=None, longitude=None):
    db.add(TrackingEvent(company_id=actor.company_id, delivery_id=delivery.id, status=event_status, description=description, latitude=latitude, longitude=longitude, created_by_user_id=actor.id))


def list_tracking(db: Session, company_id: UUID, delivery_id: UUID) -> list[TrackingEvent]:
    delivery = _get_delivery(db, company_id, delivery_id)
    return list(db.scalars(select(TrackingEvent).where(TrackingEvent.delivery_id == delivery.id, TrackingEvent.company_id == company_id).order_by(TrackingEvent.occurred_at.asc())).all())


def create_route(db: Session, actor: User, payload: RouteCreate, request=None) -> DeliveryRoute:
    _warehouse(db, actor.company_id, payload.warehouse_id); _driver(db, actor.company_id, payload.driver_id); _vehicle(db, actor.company_id, payload.vehicle_id)
    item = DeliveryRoute(company_id=actor.company_id, warehouse_id=payload.warehouse_id, driver_id=payload.driver_id, vehicle_id=payload.vehicle_id, route_number=f"ROT-{uuid4().hex[:12].upper()}", route_date=payload.route_date, notes=payload.notes)
    db.add(item); db.flush()
    record_audit(db, request=request, action="delivery_route.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="delivery_route", resource_id=item.id, metadata={"route_number": item.route_number})
    db.commit(); db.refresh(item); return item


def add_route_stop(db: Session, actor: User, route: DeliveryRoute, payload: RouteStopCreate, request=None) -> RouteStop:
    delivery = _get_delivery(db, actor.company_id, payload.delivery_id)
    if delivery.status not in {"assigned", "pending", "failed"}:
        raise HTTPException(status_code=409, detail="Only pending, assigned, or failed deliveries can be added to a route")
    if delivery.warehouse_id != route.warehouse_id:
        raise HTTPException(status_code=409, detail="Delivery warehouse does not match route warehouse")
    if delivery.driver_id is not None and delivery.driver_id != route.driver_id:
        raise HTTPException(status_code=409, detail="Delivery driver does not match route driver")
    if delivery.vehicle_id is not None and delivery.vehicle_id != route.vehicle_id:
        raise HTTPException(status_code=409, detail="Delivery vehicle does not match route vehicle")
    duplicate = db.scalar(select(RouteStop).where(RouteStop.route_id == route.id, RouteStop.delivery_id == delivery.id))
    if duplicate: raise HTTPException(status_code=409, detail="Delivery is already on this route")
    sequence_conflict = db.scalar(select(RouteStop).where(RouteStop.route_id == route.id, RouteStop.sequence == payload.sequence))
    if sequence_conflict: raise HTTPException(status_code=409, detail="Route sequence already in use")
    stop = RouteStop(company_id=actor.company_id, route_id=route.id, delivery_id=delivery.id, sequence=payload.sequence)
    db.add(stop); delivery.route_id = route.id; db.flush()
    record_audit(db, request=request, action="delivery_route.stop_added", company_id=actor.company_id, actor_user_id=actor.id, resource_type="delivery_route", resource_id=route.id, metadata={"delivery_id": str(delivery.id), "sequence": payload.sequence})
    db.commit(); db.refresh(stop); return stop


def get_route(db: Session, company_id: UUID, route_id: UUID) -> DeliveryRoute:
    route = db.scalar(select(DeliveryRoute).where(DeliveryRoute.id == route_id, DeliveryRoute.company_id == company_id))
    if route is None: raise HTTPException(status_code=404, detail="Delivery route not found")
    return route


def update_route_status(db: Session, actor: User, route: DeliveryRoute, new_status: str, request=None) -> DeliveryRoute:
    transitions = {"planned": {"in_progress", "cancelled"}, "in_progress": {"completed", "cancelled"}, "completed": set(), "cancelled": set()}
    if new_status not in transitions.get(route.status, set()): raise HTTPException(status_code=409, detail=f"Cannot transition route from {route.status} to {new_status}")
    route.status = new_status; db.flush()
    record_audit(db, request=request, action="delivery_route.status_changed", company_id=actor.company_id, actor_user_id=actor.id, resource_type="delivery_route", resource_id=route.id, metadata={"status": new_status})
    db.commit(); db.refresh(route); return route
