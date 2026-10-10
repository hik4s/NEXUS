from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.identity.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.company import Company
from app.models.user import User
from app.models.rbac import Role
from app.rbac.service import ensure_rbac_seed, get_role_names
from app.schemas.auth import RegisterRequest



def register_owner(db: Session, payload: RegisterRequest, request=None) -> tuple[User, str, str]:
    ensure_rbac_seed(db)
    existing_email = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if existing_email:
        raise ValueError("Email already registered")

    existing_company = db.scalar(
        select(Company).where(
            (Company.slug == payload.company_slug) | (Company.name == payload.company_name)
        )
    )
    if existing_company:
        raise ValueError("Company name or slug already registered")

    admin_role = db.scalar(select(Role).where(Role.key == "admin"))
    assert admin_role is not None

    company = Company(name=payload.company_name, slug=payload.company_slug)
    user = User(
        company=company,
        full_name=payload.full_name,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role="admin",
    )
    user.roles.append(admin_role)
    db.add(company)
    db.add(user)
    db.flush()
    record_audit(
        db,
        request=request,
        action="auth.register",
        company_id=company.id,
        actor_user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        metadata={"role": "admin"},
    )
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id), create_refresh_token(user.id)


def authenticate_user(db: Session, email: str, password: str, request=None) -> tuple[User, str, str] | None:
    normalized_email = email.lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        record_audit(db, request=request, action="auth.login", status="failure", metadata={"reason": "unknown_email"})
        db.commit()
        return None
    if not user.is_active or not verify_password(password, user.password_hash):
        record_audit(
            db,
            request=request,
            action="auth.login",
            company_id=user.company_id,
            actor_user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            status="failure",
            metadata={"reason": "invalid_credentials"},
        )
        db.commit()
        return None

    record_audit(
        db,
        request=request,
        action="auth.login",
        company_id=user.company_id,
        actor_user_id=user.id,
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return user, create_access_token(user.id), create_refresh_token(user.id)
