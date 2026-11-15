from fastapi import APIRouter, Depends, HTTPException, Request, status
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.identity.dependencies import get_current_user, bearer_scheme
from fastapi.security import HTTPAuthorizationCredentials
from app.identity.supabase import verify_identity
from app.services.external_auth_service import provision_workspace
from app.identity.security import create_access_token, create_refresh_token, decode_refresh_token
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import authenticate_user, register_owner
from app.services.presentation import user_response

router = APIRouter(prefix="/auth")


def require_legacy_auth() -> None:
    if settings.AUTH_PROVIDER != 'legacy':
        raise HTTPException(403, detail={'code':'managed_auth','message':'Use o login do Supabase.'})


@router.post('/bootstrap', response_model=UserResponse)
def bootstrap(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
              db: Session = Depends(get_db)) -> UserResponse:
    if settings.AUTH_PROVIDER != 'supabase':
        raise HTTPException(404, detail='External auth is not enabled')
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(401, detail='Authentication required')
    identity=verify_identity(credentials.credentials)
    return user_response(provision_workspace(db,identity,request=request))



@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    require_legacy_auth()
    if not settings.PUBLIC_REGISTRATION_ENABLED:
        raise HTTPException(status_code=403, detail={'code': 'registration_disabled', 'message': 'Cadastro público indisponível.'})
    try:
        user, access_token, refresh_token = register_owner(db, payload, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    require_legacy_auth()
    result = authenticate_user(db, str(payload.email), payload.password, request=request)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    user, access_token, refresh_token = result
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    require_legacy_auth()
    try:
        user_id = decode_refresh_token(payload.refresh_token)
    except (ValueError, TypeError, InvalidTokenError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=user_response(user),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return user_response(current_user)
