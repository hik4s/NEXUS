from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.lead import Lead
from app.models.user import User
from app.schemas.crm import CustomerCreate, CustomerUpdate, InteractionCreate, LeadCreate, LeadUpdate


def _company_user(db: Session, company_id: UUID, user_id: UUID | None) -> User | None:
    if user_id is None:
        return None
    return db.scalar(select(User).where(User.id == user_id, User.company_id == company_id))


def get_customer(db: Session, company_id: UUID, customer_id: UUID) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.id == customer_id, Customer.company_id == company_id))


def create_customer(db: Session, actor: User, payload: CustomerCreate, request=None) -> Customer:
    email = str(payload.email).lower() if payload.email else None
    if email and db.scalar(select(Customer).where(Customer.company_id == actor.company_id, Customer.email == email)):
        raise ValueError("Customer email already exists in this company")
    customer = Customer(
        company_id=actor.company_id,
        name=payload.name,
        email=email,
        phone=payload.phone,
        tax_id=payload.tax_id,
        status=payload.status,
        source=payload.source,
        notes=payload.notes,
    )
    db.add(customer)
    db.flush()
    record_audit(
        db, request=request, action="customer.created", company_id=actor.company_id,
        actor_user_id=actor.id, resource_type="customer", resource_id=customer.id,
        metadata={"name": customer.name, "email": customer.email},
    )
    db.commit(); db.refresh(customer)
    return customer


def update_customer(db: Session, actor: User, customer: Customer, payload: CustomerUpdate, request=None) -> Customer:
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = str(data["email"]).lower()
        duplicate = db.scalar(
            select(Customer).where(
                Customer.company_id == actor.company_id,
                Customer.email == data["email"],
                Customer.id != customer.id,
            )
        )
        if duplicate:
            raise ValueError("Customer email already exists in this company")
    for key, value in data.items():
        setattr(customer, key, value)
    db.flush()
    record_audit(
        db, request=request, action="customer.updated", company_id=actor.company_id,
        actor_user_id=actor.id, resource_type="customer", resource_id=customer.id,
        metadata={"fields": sorted(data.keys())},
    )
    db.commit(); db.refresh(customer)
    return customer


def get_lead(db: Session, company_id: UUID, lead_id: UUID) -> Lead | None:
    return db.scalar(select(Lead).where(Lead.id == lead_id, Lead.company_id == company_id))


def create_lead(db: Session, actor: User, payload: LeadCreate, request=None) -> Lead:
    customer = None
    if payload.customer_id is not None:
        customer = get_customer(db, actor.company_id, payload.customer_id)
        if customer is None:
            raise ValueError("Customer not found")
    assigned = _company_user(db, actor.company_id, payload.assigned_to_user_id)
    if payload.assigned_to_user_id is not None and assigned is None:
        raise ValueError("Assigned user not found in this company")
    lead = Lead(
        company_id=actor.company_id,
        customer_id=customer.id if customer else None,
        assigned_to_user_id=assigned.id if assigned else None,
        name=payload.name,
        email=str(payload.email).lower() if payload.email else None,
        phone=payload.phone,
        source=payload.source,
        status=payload.status,
        expected_value=payload.expected_value,
        notes=payload.notes,
    )
    db.add(lead); db.flush()
    record_audit(
        db, request=request, action="lead.created", company_id=actor.company_id,
        actor_user_id=actor.id, resource_type="lead", resource_id=lead.id,
        metadata={"name": lead.name, "status": lead.status},
    )
    db.commit(); db.refresh(lead)
    return lead


def update_lead(db: Session, actor: User, lead: Lead, payload: LeadUpdate, request=None) -> Lead:
    data = payload.model_dump(exclude_unset=True)
    if "customer_id" in data and data["customer_id"] is not None:
        if get_customer(db, actor.company_id, data["customer_id"]) is None:
            raise ValueError("Customer not found")
    if "assigned_to_user_id" in data and data["assigned_to_user_id"] is not None:
        if _company_user(db, actor.company_id, data["assigned_to_user_id"]) is None:
            raise ValueError("Assigned user not found in this company")
    if "email" in data and data["email"]:
        data["email"] = str(data["email"]).lower()
    for key, value in data.items():
        setattr(lead, key, value)
    db.flush()
    record_audit(
        db, request=request, action="lead.updated", company_id=actor.company_id,
        actor_user_id=actor.id, resource_type="lead", resource_id=lead.id,
        metadata={"fields": sorted(data.keys()), "status": lead.status},
    )
    db.commit(); db.refresh(lead)
    return lead


def create_interaction(db: Session, actor: User, payload: InteractionCreate, request=None) -> Interaction:
    customer = get_customer(db, actor.company_id, payload.customer_id) if payload.customer_id else None
    lead = get_lead(db, actor.company_id, payload.lead_id) if payload.lead_id else None
    if payload.customer_id and customer is None:
        raise ValueError("Customer not found")
    if payload.lead_id and lead is None:
        raise ValueError("Lead not found")
    interaction = Interaction(
        company_id=actor.company_id,
        customer_id=customer.id if customer else None,
        lead_id=lead.id if lead else None,
        actor_user_id=actor.id,
        type=payload.type,
        channel=payload.channel,
        subject=payload.subject,
        content=payload.content,
        occurred_at=payload.occurred_at,
    )
    db.add(interaction); db.flush()
    record_audit(
        db, request=request, action="interaction.created", company_id=actor.company_id,
        actor_user_id=actor.id, resource_type="interaction", resource_id=interaction.id,
        metadata={"type": interaction.type, "channel": interaction.channel},
    )
    db.commit(); db.refresh(interaction)
    return interaction
