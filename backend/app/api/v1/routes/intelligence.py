
from uuid import UUID
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.audit.service import record_audit
from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.intelligence.actions import approve_proposal, execute_proposal, get_proposal, reject_proposal
from app.intelligence.gateway import generate_reply
from app.models.intelligence import ActionProposal, IntelligenceConversation, IntelligenceMessage
from app.models.user import User
from app.schemas.intelligence import ActionProposalRead, ActionReject, ConversationCreate, ConversationRead, MessageCreate, MessageRead

router = APIRouter(prefix="/intelligence")


def _conversation(db: Session, company_id: UUID, user_id: UUID, conversation_id: UUID) -> IntelligenceConversation:
    item = db.scalar(select(IntelligenceConversation).options(selectinload(IntelligenceConversation.messages)).where(IntelligenceConversation.id == conversation_id, IntelligenceConversation.company_id == company_id, IntelligenceConversation.user_id == user_id))
    if item is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item

@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, request: Request, current_user: User = Depends(require_permission("intelligence:chat")), db: Session = Depends(get_db)):
    item = IntelligenceConversation(company_id=current_user.company_id, user_id=current_user.id, title=payload.title)
    db.add(item); db.flush()
    record_audit(db, request=request, action="intelligence.conversation.created", company_id=current_user.company_id, actor_user_id=current_user.id, resource_type="intelligence_conversation", resource_id=item.id)
    db.commit(); return _conversation(db, current_user.company_id, current_user.id, item.id)

@router.get("/conversations", response_model=list[ConversationRead])
def list_conversations(current_user: User = Depends(require_permission("intelligence:read")), db: Session = Depends(get_db)):
    return list(db.scalars(select(IntelligenceConversation).options(selectinload(IntelligenceConversation.messages)).where(IntelligenceConversation.company_id == current_user.company_id, IntelligenceConversation.user_id == current_user.id).order_by(IntelligenceConversation.updated_at.desc())).unique().all())

@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: UUID, current_user: User = Depends(require_permission("intelligence:read")), db: Session = Depends(get_db)):
    return _conversation(db, current_user.company_id, current_user.id, conversation_id)

@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead)
def send_message(conversation_id: UUID, payload: MessageCreate, request: Request, current_user: User = Depends(require_permission("intelligence:chat")), db: Session = Depends(get_db)):
    conversation = _conversation(db, current_user.company_id, current_user.id, conversation_id)
    db.add(IntelligenceMessage(conversation_id=conversation.id, role="user", content=payload.content))
    db.commit(); db.refresh(conversation)
    assistant = generate_reply(db, current_user, _conversation(db, current_user.company_id, current_user.id, conversation.id))
    return assistant

@router.get("/action-proposals", response_model=list[ActionProposalRead])
def list_action_proposals(current_user: User = Depends(require_permission("intelligence:read")), db: Session = Depends(get_db)):
    return list(db.scalars(select(ActionProposal).where(ActionProposal.company_id == current_user.company_id).order_by(ActionProposal.created_at.desc())).all())

@router.post("/action-proposals/{proposal_id}/approve", response_model=ActionProposalRead)
def approve_action(proposal_id: UUID, request: Request, current_user: User = Depends(require_permission("intelligence:approve")), db: Session = Depends(get_db)):
    return approve_proposal(db, current_user, get_proposal(db, current_user.company_id, proposal_id), request=request)

@router.post("/action-proposals/{proposal_id}/reject", response_model=ActionProposalRead)
def reject_action(proposal_id: UUID, payload: ActionReject, request: Request, current_user: User = Depends(require_permission("intelligence:approve")), db: Session = Depends(get_db)):
    return reject_proposal(db, current_user, get_proposal(db, current_user.company_id, proposal_id), payload.reason, request=request)

@router.post("/action-proposals/{proposal_id}/execute", response_model=ActionProposalRead)
def execute_action(proposal_id: UUID, request: Request, current_user: User = Depends(require_permission("intelligence:approve")), db: Session = Depends(get_db)):
    return execute_proposal(db, current_user, get_proposal(db, current_user.company_id, proposal_id), request=request)
