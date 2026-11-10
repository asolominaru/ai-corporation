"""Аутентификация сервисных токенов (R-01).

Личность НЕ берётся из JSON-тела: каждый вызов обязан нести
`Authorization: Bearer <token>`. Токен → {actor, role, tenant_id} задаётся
в env ORCHESTRATOR_TOKENS (JSON). ID владельца больше не является секретом:
знание owner-id без токена даёт 401.

Роли:
- admin         — справочники (tenants/projects/agents), чтение всего;
- orchestrator  — создание задач, submit, complete, approvals create;
- agent         — claim/report/review (actor = id агента);
- ci            — аттестация CI (POST /tasks/{id}/ci);
- owner         — decide/cancel/requeue (actor ∈ ORCHESTRATOR_OWNER_IDS).

P0-ограничение: статичные токены в env приватной сети; OAuth/OIDC — P2.
"""
import json
import os
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass
class Actor:
    actor_id: str
    role: str
    tenant_id: str | None  # None = сервисная роль (orchestrator/admin/ci)


def load_tokens() -> dict:
    raw = os.getenv("ORCHESTRATOR_TOKENS", "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def require_auth(request: Request) -> Actor:
    header = request.headers.get("authorization", "")
    token = header[7:] if header.startswith("Bearer ") else None
    rec = load_tokens().get(token or "")
    if not rec:
        raise HTTPException(401, "требуется действительный service token")
    return Actor(rec["actor"], rec["role"], rec.get("tenant_id"))


def require_role(actor: Actor, *roles: str):
    if actor.role not in roles:
        raise HTTPException(403, f"роль {actor.role} не имеет права на это действие")


def check_tenant_scope(actor: Actor, tenant_id: str):
    """Токен с привязкой к tenant действует только внутри него."""
    if actor.tenant_id and actor.tenant_id != tenant_id:
        raise HTTPException(403, "токен привязан к другому tenant")
