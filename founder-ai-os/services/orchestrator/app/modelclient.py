"""Единственный путь к моделям из контура orchestrator (п.3 повторной
проверки): агентские workers вызывают ТОЛЬКО model-router. Прямой импорт
провайдеров или обращение к API моделей минуя router запрещены — здесь
нет и не будет кода прямого вызова.

Аутентификация — service token роли orchestrator (MODEL_ROUTER_TOKEN).
Бюджет задачи передаётся в каждый вызов: router блокирует платный вызов
без лимита (закон 7) и ведёт резервы task+day+month (R-04).
"""
from __future__ import annotations

import os

import httpx

ROUTER_URL = os.getenv("MODEL_ROUTER_URL", "http://localhost:8100")
ROUTER_TOKEN = os.getenv("MODEL_ROUTER_TOKEN", "")

TIMEOUT = httpx.Timeout(120.0, connect=10.0)


class RouterError(Exception):
    """Любой отказ router'а (бюджет, нет маршрута, провайдер упал)."""

    def __init__(self, status: int, detail: str):
        super().__init__(f"router HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


def complete(*, tenant_id: str, task_id: str, task_type: str,
             messages: list[dict], task_budget_max_usd: float,
             data_privacy: str = "public", avoid_model_id: str | None = None,
             est_tokens_in: int = 4000, max_tokens_out: int = 2000,
             client: httpx.Client | None = None) -> dict:
    """Вызов модели через router. Возвращает ответ router'а:
    {run_id, model, text, usage, task_spent_usd, overrun}.

    client — для тестов (ASGI transport); в проде создаётся здесь
    с base_url=MODEL_ROUTER_URL.
    """
    payload = {
        "tenant_id": tenant_id,
        "task_id": task_id,
        "task_type": task_type,
        "messages": messages,
        "data_privacy": data_privacy,
        "task_budget_max_usd": task_budget_max_usd,
        "avoid_model_id": avoid_model_id,
        "est_tokens_in": est_tokens_in,
        "max_tokens_out": max_tokens_out,
    }
    headers = {"Authorization": f"Bearer {ROUTER_TOKEN}"}

    if client is not None:
        resp = client.post("/complete", json=payload, headers=headers)
    else:
        if not ROUTER_TOKEN:
            raise RouterError(0, "MODEL_ROUTER_TOKEN не задан — вызов невозможен")
        with httpx.Client(base_url=ROUTER_URL, timeout=TIMEOUT) as c:
            resp = c.post("/complete", json=payload, headers=headers)

    if resp.status_code != 200:
        raise RouterError(resp.status_code, resp.text[:300])
    return resp.json()
