from app.identity.security import create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.rbac.service import get_role_names


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        company_id=user.company_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        roles=get_role_names(user),
    )


def token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=user_response(user),
    )
