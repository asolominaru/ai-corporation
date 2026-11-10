"""Аутентификация model-router (R-03).

ROUTER_TOKENS (env, JSON): {"<token>": {"actor": ..., "role": ..., "tenant_id": ...}}
- admin        — управление реестром моделей (регистрация/вывод из эксплуатации);
- orchestrator — вызовы /complete; tenant_id токена обязан совпадать с запросом.

Клиенты (браузер/UI) токенов router'а НЕ имеют — вызывает только orchestrator.
"""
import json
import os
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass
class Actor:
    actor_id: str
    role: str
    tenant_id: str | None


def load_tokens() -> dict:
    raw = os.getenv("ROUTER_TOKENS", "")
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
