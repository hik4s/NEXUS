
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings


@dataclass
class ToolCallRequest:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderResponse:
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    provider: str = "unknown"
    model: str = "unknown"
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0


class ProviderError(RuntimeError):
    pass


class MockProvider:
    name = "mock"

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, model: str, max_output_tokens: int) -> ProviderResponse:
        start = time.perf_counter()
        if messages and messages[-1].get("role") == "tool":
            content = messages[-1].get("content", "")
            text = f"Consultei os dados solicitados e encontrei: {content}. Use esses dados como evidência para a resposta."
            return ProviderResponse(content=text[:max_output_tokens * 6], provider=self.name, model=model, usage={"input_tokens": 0, "output_tokens": min(len(text.split()), max_output_tokens)}, latency_ms=int((time.perf_counter()-start)*1000))
        last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "").lower()
        tool_names = {t["name"] for t in tools}
        call = None
        if any(w in last_user for w in ("crie uma tarefa", "abra uma tarefa", "criar uma tarefa")) and "actions.propose_workflow_task" in tool_names:
            call = ToolCallRequest("mock-task-1", "actions.propose_workflow_task", {"title": "Revisar ponto identificado pelo NEXUS", "description": "Tarefa proposta a partir da conversa com o NEXUS.", "priority": "normal"})
        elif any(w in last_user for w in ("venda", "vendas", "faturamento", "faturei")) and "metrics.sales_summary" in tool_names:
            call = ToolCallRequest("mock-sales-1", "metrics.sales_summary", {"days": 30})
        elif any(w in last_user for w in ("estoque", "inventário", "inventario")) and "metrics.inventory_summary" in tool_names:
            call = ToolCallRequest("mock-inventory-1", "metrics.inventory_summary", {})
        elif any(w in last_user for w in ("caixa", "dinheiro", "saldo")) and "metrics.cash_summary" in tool_names:
            call = ToolCallRequest("mock-cash-1", "metrics.cash_summary", {})
        elif any(w in last_user for w in ("inadimpl", "vencida", "vencidas")) and "metrics.overdue_receivables" in tool_names:
            call = ToolCallRequest("mock-ar-1", "metrics.overdue_receivables", {})
        elif any(w in last_user for w in ("fornecedor", "fornecedores", "custo de compra")) and "metrics.supplier_price_overview" in tool_names:
            call = ToolCallRequest("mock-supplier-1", "metrics.supplier_price_overview", {})
        else:
            content = "Estou operando em modo local. Posso consultar vendas, estoque, caixa, inadimplência e preços de fornecedores, ou propor uma tarefa para aprovação."
            return ProviderResponse(content=content, provider=self.name, model=model, usage={"input_tokens": 0, "output_tokens": min(len(content.split()), max_output_tokens)}, latency_ms=int((time.perf_counter()-start)*1000))
        return ProviderResponse(content=None, tool_calls=[call], provider=self.name, model=model, usage={}, latency_ms=int((time.perf_counter()-start)*1000))


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self) -> None:
        if not settings.AI_BASE_URL or not settings.AI_API_KEY:
            raise ProviderError("AI_BASE_URL and AI_API_KEY are required for the configured provider")

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, model: str, max_output_tokens: int) -> ProviderResponse:
        start = time.perf_counter()
        payload = {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": max_output_tokens}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
        headers = {"Authorization": f"Bearer {settings.AI_API_KEY}", "Content-Type": "application/json"}
        try:
            with httpx.Client(base_url=settings.AI_BASE_URL.rstrip("/"), timeout=settings.AI_TIMEOUT_SECONDS) as client:
                response = client.post("/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise ProviderError(str(exc)) from exc
        choice = data.get("choices", [{}])[0].get("message", {})
        tool_calls = []
        for item in choice.get("tool_calls") or []:
            fn = item.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError as exc:
                raise ProviderError(f"Invalid tool arguments returned by provider: {exc}") from exc
            tool_calls.append(ToolCallRequest(str(item.get("id")), str(fn.get("name")), args))
        return ProviderResponse(content=choice.get("content"), tool_calls=tool_calls, provider=self.name, model=data.get("model", model), usage=data.get("usage") or {}, latency_ms=int((time.perf_counter()-start)*1000))


def build_provider():
    if settings.AI_PROVIDER == "openai-compatible":
        return OpenAICompatibleProvider()
    return MockProvider()
