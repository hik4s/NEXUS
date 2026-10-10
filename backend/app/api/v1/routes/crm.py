from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.lead import Lead
from app.models.user import User
from app.schemas.crm import (
    CustomerCreate, CustomerRead, CustomerUpdate, InteractionCreate, InteractionRead,
    LeadCreate, LeadRead, LeadUpdate,
)
from app.services.crm_service import create_customer, create_interaction, create_lead, get_customer, get_lead, update_customer, update_lead
from app.platform.service import apply_pagination_headers, paginate_statement

router = APIRouter(prefix="/crm")


@router.get("/customers", response_model=list[CustomerRead])
def list_customers(
    response: Response,
    q: str | None = Query(default=None, min_length=1, max_length=120),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|inactive)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_permission("customers:read")),
    db: Session = Depends(get_db),
) -> list[Customer]:
    stmt = select(Customer).where(Customer.company_id == current_user.company_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Customer.name.ilike(like)) | (Customer.email.ilike(like)))
    if status_filter:
        stmt = stmt.where(Customer.status == status_filter)
    sort_field = Customer.name
    sort_order = "asc"
    items, meta = paginate_statement(db, stmt.order_by(sort_field.asc()), page=page, page_size=page_size)
    apply_pagination_headers(response, meta)
    return items


@router.post("/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer_route(
    payload: CustomerCreate,
    request: Request,
    current_user: User = Depends(require_permission("customers:write")),
    db: Session = Depends(get_db),
) -> Customer:
    try:
        return create_customer(db, current_user, payload, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/customers/{customer_id}", response_model=CustomerRead)
def get_customer_route(
    customer_id: UUID,
    current_user: User = Depends(require_permission("customers:read")),
    db: Session = Depends(get_db),
) -> Customer:
    customer = get_customer(db, current_user.company_id, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerRead)
def update_customer_route(
    customer_id: UUID,
    payload: CustomerUpdate,
    request: Request,
    current_user: User = Depends(require_permission("customers:write")),
    db: Session = Depends(get_db),
) -> Customer:
    customer = get_customer(db, current_user.company_id, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    try:
        return update_customer(db, current_user, customer, payload, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/leads", response_model=list[LeadRead])
def list_leads(
    response: Response,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(new|qualified|proposal|won|lost)$"),
    assigned_to_user_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_permission("leads:read")),
    db: Session = Depends(get_db),
) -> list[Lead]:
    stmt = select(Lead).where(Lead.company_id == current_user.company_id)
    if status_filter:
        stmt = stmt.where(Lead.status == status_filter)
    if assigned_to_user_id:
        stmt = stmt.where(Lead.assigned_to_user_id == assigned_to_user_id)
    items, meta = paginate_statement(db, stmt.order_by(Lead.created_at.desc()), page=page, page_size=page_size)
    apply_pagination_headers(response, meta)
    return items


@router.post("/leads", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead_route(
    payload: LeadCreate,
    request: Request,
    current_user: User = Depends(require_permission("leads:write")),
    db: Session = Depends(get_db),
) -> Lead:
    try:
        return create_lead(db, current_user, payload, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/leads/{lead_id}", response_model=LeadRead)
def get_lead_route(
    lead_id: UUID,
    current_user: User = Depends(require_permission("leads:read")),
    db: Session = Depends(get_db),
) -> Lead:
    lead = get_lead(db, current_user.company_id, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/leads/{lead_id}", response_model=LeadRead)
def update_lead_route(
    lead_id: UUID,
    payload: LeadUpdate,
    request: Request,
    current_user: User = Depends(require_permission("leads:write")),
    db: Session = Depends(get_db),
) -> Lead:
    lead = get_lead(db, current_user.company_id, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        return update_lead(db, current_user, lead, payload, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/interactions", response_model=list[InteractionRead])
def list_interactions(
    customer_id: UUID | None = None,
    lead_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("interactions:read")),
    db: Session = Depends(get_db),
) -> list[Interaction]:
    if customer_id and get_customer(db, current_user.company_id, customer_id) is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if lead_id and get_lead(db, current_user.company_id, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    stmt = select(Interaction).where(Interaction.company_id == current_user.company_id)
    if customer_id:
        stmt = stmt.where(Interaction.customer_id == customer_id)
    if lead_id:
        stmt = stmt.where(Interaction.lead_id == lead_id)
    return list(db.scalars(stmt.order_by(Interaction.occurred_at.desc()).offset(offset).limit(limit)).all())


@router.post("/interactions", response_model=InteractionRead, status_code=status.HTTP_201_CREATED)
def create_interaction_route(
    payload: InteractionCreate,
    request: Request,
    current_user: User = Depends(require_permission("interactions:write")),
    db: Session = Depends(get_db),
) -> Interaction:
    try:
        return create_interaction(db, current_user, payload, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
