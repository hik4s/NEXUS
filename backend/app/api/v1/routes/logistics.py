from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.logistics import Delivery, DeliveryRoute, Driver, RouteStop, TrackingEvent, Vehicle
from app.models.user import User
from app.schemas.logistics import DeliveryAssign, DeliveryCreate, DeliveryRead, DeliveryStatusUpdate, DriverCreate, DriverRead, RouteCreate, RouteRead, RouteStatusUpdate, RouteStopCreate, RouteStopRead, TrackingEventRead, VehicleCreate, VehicleRead
from app.services.logistics_service import add_route_stop, assign_delivery, create_delivery, create_driver, create_route, create_vehicle, get_delivery, get_route, list_deliveries, list_drivers, list_tracking, list_vehicles, update_delivery_status, update_route_status

router = APIRouter(prefix="/logistics")


@router.get("/drivers", response_model=list[DriverRead])
def get_drivers(current_user: User = Depends(require_permission("logistics:read")), db: Session = Depends(get_db)) -> list[Driver]:
    return list_drivers(db, current_user.company_id)


@router.post("/drivers", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
def post_driver(payload: DriverCreate, request: Request, current_user: User = Depends(require_permission("logistics:write")), db: Session = Depends(get_db)) -> Driver:
    return create_driver(db, current_user, payload, request=request)


@router.get("/vehicles", response_model=list[VehicleRead])
def get_vehicles(current_user: User = Depends(require_permission("logistics:read")), db: Session = Depends(get_db)) -> list[Vehicle]:
    return list_vehicles(db, current_user.company_id)


@router.post("/vehicles", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def post_vehicle(payload: VehicleCreate, request: Request, current_user: User = Depends(require_permission("logistics:write")), db: Session = Depends(get_db)) -> Vehicle:
    return create_vehicle(db, current_user, payload, request=request)


@router.get("/deliveries", response_model=list[DeliveryRead])
def get_deliveries(status_filter: str | None = None, current_user: User = Depends(require_permission("logistics:read")), db: Session = Depends(get_db)) -> list[Delivery]:
    return list_deliveries(db, current_user.company_id, status_filter)


@router.post("/deliveries", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED)
def post_delivery(payload: DeliveryCreate, request: Request, current_user: User = Depends(require_permission("logistics:write")), db: Session = Depends(get_db)) -> Delivery:
    return create_delivery(db, current_user, payload, request=request)


@router.get("/deliveries/{delivery_id}", response_model=DeliveryRead)
def get_delivery_route(delivery_id: UUID, current_user: User = Depends(require_permission("logistics:read")), db: Session = Depends(get_db)) -> Delivery:
    return get_delivery(db, current_user.company_id, delivery_id)


@router.patch("/deliveries/{delivery_id}/assign", response_model=DeliveryRead)
def assign_delivery_route(delivery_id: UUID, payload: DeliveryAssign, request: Request, current_user: User = Depends(require_permission("logistics:assign")), db: Session = Depends(get_db)) -> Delivery:
    delivery = get_delivery(db, current_user.company_id, delivery_id)
    return assign_delivery(db, current_user, delivery, payload, request=request)


@router.patch("/deliveries/{delivery_id}/status", response_model=DeliveryRead)
def status_delivery(delivery_id: UUID, payload: DeliveryStatusUpdate, request: Request, current_user: User = Depends(require_permission("logistics:deliver")), db: Session = Depends(get_db)) -> Delivery:
    delivery = get_delivery(db, current_user.company_id, delivery_id)
    return update_delivery_status(db, current_user, delivery, payload, request=request)


@router.get("/deliveries/{delivery_id}/tracking", response_model=list[TrackingEventRead])
def get_tracking(delivery_id: UUID, current_user: User = Depends(require_permission("logistics:read")), db: Session = Depends(get_db)) -> list[TrackingEvent]:
    return list_tracking(db, current_user.company_id, delivery_id)


@router.get("/routes/{route_id}", response_model=RouteRead)
def get_route_route(route_id: UUID, current_user: User = Depends(require_permission("logistics:read")), db: Session = Depends(get_db)) -> DeliveryRoute:
    return get_route(db, current_user.company_id, route_id)


@router.post("/routes", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
def post_route(payload: RouteCreate, request: Request, current_user: User = Depends(require_permission("logistics:write")), db: Session = Depends(get_db)) -> DeliveryRoute:
    return create_route(db, current_user, payload, request=request)


@router.post("/routes/{route_id}/stops", response_model=RouteStopRead, status_code=status.HTTP_201_CREATED)
def post_stop(route_id: UUID, payload: RouteStopCreate, request: Request, current_user: User = Depends(require_permission("logistics:assign")), db: Session = Depends(get_db)) -> RouteStop:
    route = get_route(db, current_user.company_id, route_id)
    return add_route_stop(db, current_user, route, payload, request=request)


@router.patch("/routes/{route_id}/status", response_model=RouteRead)
def route_status(route_id: UUID, payload: RouteStatusUpdate, request: Request, current_user: User = Depends(require_permission("logistics:dispatch")), db: Session = Depends(get_db)) -> DeliveryRoute:
    route = get_route(db, current_user.company_id, route_id)
    return update_route_status(db, current_user, route, payload.status, request=request)
