"""Own-company provisioning; provider metadata never selects tenants or permissions."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.identity.supabase import ExternalIdentity
from app.models.company import Company
from app.models.user import User
from app.models.rbac import Role

def external_user(db: Session, identity: ExternalIdentity) -> User | None:
    return db.scalar(select(User).where(User.supabase_subject==identity.subject))

def active(user: User) -> User:
    if not user.is_active:
        raise HTTPException(403, detail={'code':'account_inactive','message':'Esta conta está desativada.'})
    return user

def provision_workspace(db: Session, identity: ExternalIdentity, request=None) -> User:
    existing=external_user(db,identity)
    if existing:
        return active(existing)
    if db.scalar(select(User.id).where(User.email==identity.email)):
        raise HTTPException(409, detail={'code':'account_link_required','message':'Este e-mail já possui conta legada. Solicite a migração do acesso.'})
    role=db.scalar(select(Role).where(Role.key=='admin'))
    if role is None:
        raise HTTPException(503, detail={'code':'auth_unavailable','message':'O workspace está iniciando. Tente novamente.'})
    company=Company(name=f'Workspace de {identity.name[:100]} · {identity.subject.hex[:12]}',slug=f'workspace-{identity.subject.hex}')
    user=User(company=company,full_name=identity.name,email=identity.email,
              supabase_subject=identity.subject,password_hash='supabase:external',role='admin')
    user.roles.append(role)
    db.add(company)
    db.add(user)
    try:
        db.flush()
        record_audit(db,request=request,action='auth.workspace_created',company_id=company.id,
                     actor_user_id=user.id,resource_type='user',resource_id=user.id,
                     metadata={'identity_provider':'supabase'})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing=external_user(db,identity)
        if existing:
            return active(existing)
        raise HTTPException(409,detail={'code':'account_link_required','message':'Não foi possível vincular a conta. Solicite a revisão do acesso.'}) from exc
    db.refresh(user)
    return user
