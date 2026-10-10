
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.intelligence import metrics
from app.models.intelligence import ActionProposal
from app.models.user import User


@dataclass(frozen=True)
class ToolContext:
    db: Session
    user: User
    conversation_id: UUID


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[ToolContext, dict[str, Any]], dict[str, Any]]


def _sales(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    days = int(args.get("days", 30))
    if not 1 <= days <= 365:
        raise HTTPException(status_code=422, detail="days must be between 1 and 365")
    return metrics.sales_summary(ctx.db, ctx.user.company_id, days)


def _inventory(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return metrics.inventory_summary(ctx.db, ctx.user.company_id)


def _cash(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return metrics.cash_summary(ctx.db, ctx.user.company_id)


def _receivables(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return metrics.overdue_receivables(ctx.db, ctx.user.company_id)


def _suppliers(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return metrics.supplier_price_overview(ctx.db, ctx.user.company_id)


def _propose_task(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    title = str(args.get("title", "Tarefa sugerida pelo NEXUS"))[:220]
    description = str(args.get("description", "Ação sugerida pela camada de Intelligence."))[:5000]
    priority = str(args.get("priority", "normal"))
    if priority not in {"low", "normal", "high", "urgent"}:
        raise HTTPException(status_code=422, detail="Invalid priority")
    proposal = ActionProposal(
        company_id=ctx.user.company_id,
        conversation_id=ctx.conversation_id,
        proposed_by_user_id=ctx.user.id,
        action_type="workflow.create_task",
        title=title,
        description=description,
        parameters_json={"title": title, "description": description, "priority": priority},
        status="pending",
    )
    ctx.db.add(proposal)
    ctx.db.flush()
    return {"proposal_id": str(proposal.id), "status": proposal.status, "action_type": proposal.action_type, "title": proposal.title}


TOOLS = {
    "metrics.sales_summary": ToolSpec("metrics.sales_summary", "Revenue and order metrics for a period.", {"type": "object", "properties": {"days": {"type": "integer"}}}, _sales),
    "metrics.inventory_summary": ToolSpec("metrics.inventory_summary", "Current inventory totals and critical items.", {"type": "object", "properties": {}}, _inventory),
    "metrics.cash_summary": ToolSpec("metrics.cash_summary", "Current cash, open receivables, payables and net exposure.", {"type": "object", "properties": {}}, _cash),
    "metrics.overdue_receivables": ToolSpec("metrics.overdue_receivables", "Overdue accounts receivable and remaining balances.", {"type": "object", "properties": {}}, _receivables),
    "metrics.supplier_price_overview": ToolSpec("metrics.supplier_price_overview", "Supplier price ranges by product.", {"type": "object", "properties": {}}, _suppliers),
    "actions.propose_workflow_task": ToolSpec("actions.propose_workflow_task", "Create a human-approval proposal for a workflow task. Never executes the task directly.", {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "priority": {"type": "string"}}, "required": ["title", "description"]}, _propose_task),
}


def get_tool_specs() -> list[ToolSpec]:
    return list(TOOLS.values())


def execute_tool(ctx: ToolContext, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        raise HTTPException(status_code=400, detail=f"Unknown AI tool: {name}")
    return tool.handler(ctx, arguments)
