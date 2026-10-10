from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.rbac import Role
from app.models.user import User
from app.schemas.user import UserCreateRequest, UserRead, UserUpdateRequest
from app.rbac.service import get_role_names
from app.services.user_service import create_company_user, update_company_user

router = APIRouter(prefix="/users")


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        company_id=user.company_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        roles=get_role_names(user),
    )


@router.get("/roles", response_model=list[dict[str, str]])
def list_roles(
    _: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    roles = db.scalars(select(Role).where(Role.is_system.is_(True)).order_by(Role.key)).all()
    return [{"key": role.key, "name": role.name, "description": role.description or ""} for role in roles]


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    users = db.scalars(
        select(User).where(User.company_id == current_user.company_id).order_by(User.full_name.asc())
    ).all()
    return [to_user_read(user) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserRead:
    try:
        user = create_company_user(db, current_user, payload, request=request)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return to_user_read(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserRead:
    target = db.scalar(select(User).where(User.id == user_id, User.company_id == current_user.company_id))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        target = update_company_user(db, current_user, target, payload, request=request)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return to_user_read(target)
