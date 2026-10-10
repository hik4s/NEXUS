from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import Permission, Role, role_permissions, user_roles
from app.models.user import User
from app.rbac.constants import SYSTEM_ROLE_DEFINITIONS


def ensure_rbac_seed(db: Session) -> None:
    roles_by_key: dict[str, Role] = {}
    permissions_by_key: dict[str, Permission] = {}

    for role_key, definition in SYSTEM_ROLE_DEFINITIONS.items():
        role = db.scalar(select(Role).where(Role.key == role_key))
        if role is None:
            role = Role(
                key=role_key,
                name=definition["name"],
                description=definition["description"],
                is_system=True,
            )
            db.add(role)
            db.flush()
        roles_by_key[role_key] = role

        for permission_key in definition["permissions"]:
            permission = db.scalar(select(Permission).where(Permission.key == permission_key))
            if permission is None:
                permission = Permission(key=permission_key, description=permission_key)
                db.add(permission)
                db.flush()
            permissions_by_key[permission_key] = permission
            if permission not in role.permissions:
                role.permissions.append(permission)

    # Backfill legacy single-role users into the new RBAC relation.
    for user in db.scalars(select(User)).all():
        if not user.roles:
            role = roles_by_key.get(user.role, roles_by_key["employee"])
            user.roles.append(role)

    db.commit()


def user_has_permission(db: Session, user_id, permission_key: str) -> bool:
    stmt = (
        select(Permission.id)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .join(Role, Role.id == role_permissions.c.role_id)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(user_roles.c.user_id == user_id, Permission.key == permission_key)
    )
    return db.scalar(stmt) is not None


def get_role_names(user: User) -> list[str]:
    return sorted({role.key for role in user.roles})
