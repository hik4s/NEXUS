"""Validate only tokens issued by the configured Supabase Auth project."""
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID
import jwt
from fastapi import HTTPException
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from pydantic import EmailStr, TypeAdapter, ValidationError
from app.core.config import settings

@dataclass(frozen=True)
class ExternalIdentity:
    subject: UUID
    email: str
    name: str

@lru_cache(maxsize=4)
def key_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url.rstrip('/')+'/auth/v1/.well-known/jwks.json', timeout=3, lifespan=300)

def verify_identity(token: str) -> ExternalIdentity:
    try:
        header = jwt.get_unverified_header(token)
        if header.get('alg') not in {'ES256','RS256'} or not header.get('kid'):
            raise jwt.InvalidTokenError('Unsupported signing key')
        key = key_client(settings.SUPABASE_URL).get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=['ES256','RS256'],
            issuer=settings.SUPABASE_URL.rstrip('/')+'/auth/v1', audience='authenticated',
            options={'require':['sub','iss','aud','exp','iat','session_id','role']}, leeway=5)
        if claims.get('role') != 'authenticated' or claims.get('is_anonymous') is not False:
            raise jwt.InvalidTokenError('Authenticated account required')
        subject = UUID(claims['sub'])
        UUID(claims['session_id'])
        email = str(TypeAdapter(EmailStr).validate_python(claims.get('email'))).lower()
        metadata = claims.get('user_metadata')
        name = metadata.get('full_name') if isinstance(metadata,dict) else None
        name = name if isinstance(name,str) else email.split('@')[0]
        name = ''.join(c for c in name if c.isprintable()).strip()[:160] or 'Usuário'
        return ExternalIdentity(subject,email,name)
    except PyJWKClientConnectionError as exc:
        raise HTTPException(503, detail={'code':'auth_unavailable','message':'Não foi possível validar a sessão. Tente novamente.'}) from exc
    except (jwt.InvalidTokenError, PyJWKClientError, ValueError, TypeError, KeyError, ValidationError) as exc:
        raise HTTPException(401, detail={'code':'unauthorized','message':'Sessão inválida ou expirada.'}) from exc
