from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.identity.security import hash_password
from app.models.rbac import Role
from app.models.user import User
from app.rbac.constants import SYSTEM_ROLE_DEFINITIONS
from app.rbac.service import get_role_names, user_has_permission
from app.schemas.user import UserCreateRequest, UserUpdateRequest


def _validate_role_keys(role_keys: list[str]) -> None:
    unknown = sorted(set(role_keys) - set(SYSTEM_ROLE_DEFINITIONS))
    if unknown:
        raise ValueError(f"Unknown role(s): {', '.join(unknown)}")


def create_company_user(db: Session, actor: User, payload: UserCreateRequest, request=None) -> User:
    _validate_role_keys(payload.role_keys)
    if "employee" not in payload.role_keys and not user_has_permission(db, actor.id, "roles:manage"):
        raise PermissionError("Only privileged administrators can assign elevated roles")
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ValueError("Email already registered")

    roles = list(db.scalars(select(Role).where(Role.key.in_(payload.role_keys))).all())
    if len(roles) != len(set(payload.role_keys)):
        raise ValueError("One or more roles are unavailable")

    user = User(
        company_id=actor.company_id,
        full_name=payload.full_name,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role_keys[0],
    )
    user.roles = roles
    db.add(user)
    db.flush()
    record_audit(
        db,
        request=request,
        action="user.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="user",
        resource_id=user.id,
        metadata={"roles": get_role_names(user)},
    )
    db.commit()
    db.refresh(user)
    return user


def update_company_user(
    db: Session,
    actor: User,
    target: User,
    payload: UserUpdateRequest,
    request=None,
) -> User:
    if target.company_id != actor.company_id:
        raise PermissionError("Access denied")

    target_roles = set(get_role_names(target))
    if target.id != actor.id and target_roles.intersection({"admin", "manager"}) and not user_has_permission(db, actor.id, "roles:manage"):
        raise PermissionError("Only privileged administrators can manage privileged users")

    if target.id == actor.id and payload.is_active is False:
        raise ValueError("You cannot deactivate your own account")

    if payload.full_name is not None:
        target.full_name = payload.full_name

    if payload.role_keys is not None:
        _validate_role_keys(payload.role_keys)
        if "employee" not in payload.role_keys and not user_has_permission(db, actor.id, "roles:manage"):
            raise PermissionError("Only privileged administrators can assign elevated roles")
        roles = list(db.scalars(select(Role).where(Role.key.in_(payload.role_keys))).all())
        if len(roles) != len(set(payload.role_keys)):
            raise ValueError("One or more roles are unavailable")
        target.roles = roles
        target.role = payload.role_keys[0]

    if payload.is_active is not None:
        if payload.is_active is False and target.is_active and "admin" in get_role_names(target):
            active_admins = db.scalars(
                select(User)
                .where(User.company_id == actor.company_id, User.is_active.is_(True))
                .join(User.roles)
                .where(Role.key == "admin")
            ).all()
            if len(active_admins) <= 1:
                raise ValueError("The company must keep at least one active administrator")
        target.is_active = payload.is_active

    db.flush()
    record_audit(
        db,
        request=request,
        action="user.updated",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="user",
        resource_id=target.id,
        metadata={"roles": get_role_names(target), "is_active": target.is_active},
    )
    db.commit()
    db.refresh(target)
    return target
