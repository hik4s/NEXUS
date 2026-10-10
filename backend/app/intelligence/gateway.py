
from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.intelligence.providers import ProviderError, ProviderResponse, build_provider
from app.intelligence.tools import ToolContext, get_tool_specs, execute_tool
from app.models.intelligence import IntelligenceConversation, IntelligenceMessage, IntelligenceToolCall
from app.models.user import User


def _tool_payload():
    return [{"name": s.name, "description": s.description, "parameters": s.input_schema} for s in get_tool_specs()]


def _conversation_messages(db: Session, conversation: IntelligenceConversation) -> list[dict[str, Any]]:
    rows = sorted(conversation.messages, key=lambda m: m.created_at)
    messages = [{"role": m.role, "content": m.content or ""} for m in rows if m.role in {"user", "assistant", "system", "tool"}]
    return messages[-40:]


def _call_provider(provider, messages, tools) -> ProviderResponse:
    last_error = None
    for attempt in range(settings.AI_MAX_RETRIES + 1):
        try:
            return provider.generate(messages, tools, model=settings.AI_MODEL, max_output_tokens=settings.AI_MAX_OUTPUT_TOKENS)
        except ProviderError as exc:
            last_error = exc
            if attempt < settings.AI_MAX_RETRIES:
                time.sleep(0.2 * (2 ** attempt))
    raise last_error or ProviderError("AI provider failed")


def generate_reply(db: Session, user: User, conversation: IntelligenceConversation) -> IntelligenceMessage:
    provider = build_provider()
    messages = _conversation_messages(db, conversation)
    tools = _tool_payload()
    tool_ctx = ToolContext(db=db, user=user, conversation_id=conversation.id)
    tool_count = 0
    final: ProviderResponse | None = None

    for _ in range(settings.AI_MAX_TOOL_CALLS + 1):
        try:
            response = _call_provider(provider, messages, tools)
        except ProviderError:
            if not settings.AI_FALLBACK_TO_MOCK or getattr(provider, "name", "") == "mock":
                raise HTTPException(status_code=502, detail="AI provider unavailable")
            from app.intelligence.providers import MockProvider
            response = MockProvider().generate(messages, tools, model="nexus-mock-1", max_output_tokens=settings.AI_MAX_OUTPUT_TOKENS)

        if not response.tool_calls:
            final = response
            break
        for call in response.tool_calls:
            tool_count += 1
            if tool_count > settings.AI_MAX_TOOL_CALLS:
                raise HTTPException(status_code=429, detail="AI tool call limit exceeded")
            tool_record = IntelligenceToolCall(conversation_id=conversation.id, tool_name=call.name, arguments_json=call.arguments, status="running")
            db.add(tool_record); db.flush()
            try:
                result = execute_tool(tool_ctx, call.name, call.arguments)
                tool_record.result_json = result
                tool_record.status = "completed"
                messages.append({"role": "assistant", "content": response.content or "", "tool_calls": [{"id": call.call_id, "name": call.name, "arguments": call.arguments}]})
                messages.append({"role": "tool", "content": str(result), "tool_call_id": call.call_id})
            except Exception as exc:
                tool_record.status = "failed"
                tool_record.error_message = str(exc)
                messages.append({"role": "tool", "content": f"Tool error: {exc}", "tool_call_id": call.call_id})
            finally:
                from datetime import datetime, timezone
                tool_record.completed_at = datetime.now(timezone.utc)
                db.flush()
        if not response.tool_calls:
            final = response
            break
    if final is None:
        raise HTTPException(status_code=502, detail="AI did not return a final response")
    message = IntelligenceMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=final.content or "",
        provider=final.provider,
        model=final.model,
        usage_json=final.usage,
        metadata_json={"latency_ms": final.latency_ms, "tool_calls": tool_count},
    )
    db.add(message)
    db.commit(); db.refresh(message)
    return message
