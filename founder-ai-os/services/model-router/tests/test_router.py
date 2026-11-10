"""Тесты model-router v0.1.1: штатные сценарии + регрессии R-03/R-04
из review-2026-11-05/test_router_20261106.py (ожидают безопасного отказа
или корректного ledger). Сеть и реальные ключи не используются."""
import json
import os

os.environ["MODEL_ROUTER_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ROUTER_TOKENS"] = json.dumps({
    "tok-admin": {"actor": "admin-1", "role": "admin"},
    "tok-orch": {"actor": "orch-1", "role": "orchestrator", "tenant_id": "T"},
    "tok-orch-other": {"actor": "orch-2", "role": "orchestrator", "tenant_id": "OTHER"},
})

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app import budget, providers
from app.models import BudgetLedger

H_ADMIN = {"Authorization": "Bearer tok-admin"}
H_ORCH = {"Authorization": "Bearer tok-orch"}
H_ORCH_OTHER = {"Authorization": "Bearer tok-orch-other"}


@pytest.fixture()
def env():
    eng = create_engine("sqlite:///:memory:",
                        connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    Base.metadata.create_all(eng)
    S = sessionmaker(bind=eng)

    def override():
        with S() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c, S
    app.dependency_overrides.clear()


def register(c, endpoint=None, headers=None):
    body = {"provider": "openai", "model_name": "offline-test-model", "tier": "mid",
            "input_price_usd": 1, "output_price_usd": 1, "privacy_class": "public"}
    if endpoint:
        body["endpoint_config"] = {"base_url": endpoint}
    return c.post("/models", json=body, headers=headers or H_ADMIN)


def complete_body(**over):
    body = {"tenant_id": "T", "task_id": "A", "task_type": "writing_ux",
            "messages": [{"role": "user", "content": "offline test"}],
            "task_budget_max_usd": 1, "est_tokens_in": 100, "max_tokens_out": 100}
    body.update(over)
    return body


def stub_ok(tokens_in=100, tokens_out=100):
    return lambda *a: providers.ChatResult("stub", tokens_in, tokens_out, 1)


# --- Штатные ------------------------------------------------------------------

def test_happy_path(env, monkeypatch):
    c, S = env
    assert register(c).status_code == 201
    monkeypatch.setattr(providers, "chat", stub_ok())
    r = c.post("/complete", json=complete_body(), headers=H_ORCH)
    assert r.status_code == 200, r.text
    assert r.json()["usage"]["cost_usd"] > 0
    b = c.get("/budget/T", headers=H_ADMIN).json()
    assert b["day"]["spent_usd"] > 0 and b["day"]["reserved_usd"] == 0


def test_no_budget_no_call(env):
    c, S = env
    register(c)
    r = c.post("/complete", json=complete_body(task_budget_max_usd=None), headers=H_ORCH)
    assert r.status_code == 402  # закон 7


def test_provider_not_configured_releases_reserve(env):
    c, S = env
    register(c)
    r = c.post("/complete", json=complete_body(), headers=H_ORCH)  # ключа нет
    assert r.status_code == 503
    b = c.get("/budget/T", headers=H_ADMIN).json()
    assert b["day"]["reserved_usd"] == 0 and b["day"]["spent_usd"] == 0


# --- R-03: endpoint и реестр ----------------------------------------------------

def test_r03_registry_requires_admin(env):
    c, S = env
    assert c.post("/models", json={}).status_code == 401
    assert register(c, headers=H_ORCH).status_code == 403


def test_r03_untrusted_endpoint_rejected_at_registration(env):
    c, S = env
    r = register(c, "https://untrusted.invalid/v1")
    assert r.status_code == 422  # до любого HTTP


def test_r03_call_time_allowlist_blocks_credential_leak(env, monkeypatch):
    """Даже если запись в БД подменена мимо API, ключ не уйдёт на чужой URL:
    проверка allowlist выполняется перед HTTP-запросом."""
    c, S = env
    register(c)
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC-NOT-A-REAL-KEY")
    captured = []

    class OfflineClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, url, **kwargs):
            captured.append((url, kwargs["headers"]))
            raise AssertionError("HTTP-запрос недопустим для неразрешённого URL")

    monkeypatch.setattr(providers.httpx, "Client", OfflineClient)
    with S() as db:
        from app.models import Model
        m = db.execute(select(Model)).scalars().first()
        m.endpoint_config = {"base_url": "https://untrusted.invalid/v1"}
        db.commit()
    r = c.post("/complete", json=complete_body(), headers=H_ORCH)
    assert r.status_code in (502, 503)
    assert captured == []  # ключ никуда не отправлен


# --- R-04: бюджет ----------------------------------------------------------------

def test_r04_unauthenticated_or_foreign_tenant_rejected(env):
    c, S = env
    register(c)
    assert c.post("/complete", json=complete_body()).status_code == 401
    r = c.post("/complete", json=complete_body(), headers=H_ORCH_OTHER)
    assert r.status_code == 403  # tenant токена ≠ tenant запроса


def test_r04_overlapping_calls_respect_task_cap(env, monkeypatch):
    """Два перекрывающихся вызова одной задачи: второй не проходит резерв."""
    c, S = env
    register(c)
    body = complete_body(task_budget_max_usd=0.00031)
    entered = []

    def overlap(*a):
        if not entered:
            entered.append(True)
            inner = c.post("/complete", json=body, headers=H_ORCH)
            assert inner.status_code == 402, inner.text  # task cap атомарен
        return providers.ChatResult("stub", 100, 100, 1)

    monkeypatch.setattr(providers, "chat", overlap)
    outer = c.post("/complete", json=body, headers=H_ORCH)
    assert outer.status_code == 200, outer.text
    actual = sum(x["cost_usd"] for x in
                 c.get("/usage", params={"tenant_id": "T", "task_id": "A"},
                       headers=H_ADMIN).json())
    assert actual <= body["task_budget_max_usd"]


def test_r04_cross_month_settlement_correct(env, monkeypatch):
    """Резерв 30.11, settlement 01.12: списание идёт в периоды РЕЗЕРВА."""
    c, S = env
    monkeypatch.setattr(budget, "_current_periods", lambda: ("2026-11-30", "2026-11"))
    with S() as db:
        reserve = budget.reserve(db, tenant_id="T", task_id="A",
                                 task_cap_usd=5, amount_usd=1)
        db.commit()
        monkeypatch.setattr(budget, "_current_periods", lambda: ("2026-12-01", "2026-12"))
        budget.commit(db, reserve, 0.8)
        db.commit()
        db.expire_all()
        rows = {r.period: r for r in db.execute(select(BudgetLedger)).scalars().all()}
    assert float(rows["2026-11-30"].reserved_usd) == 0
    assert float(rows["2026-11-30"].spent_usd) == 0.8
    assert float(rows["2026-11"].spent_usd) == 0.8
    assert "2026-12-01" not in rows  # декабрь не тронут


def test_r04_settlement_idempotent(env, monkeypatch):
    c, S = env
    with S() as db:
        reserve = budget.reserve(db, tenant_id="T", task_id="A",
                                 task_cap_usd=5, amount_usd=1)
        db.commit()
        budget.commit(db, reserve, 0.8)
        with pytest.raises(ValueError):
            budget.commit(db, reserve, 0.8)  # повторный commit отклонён
        budget.release(db, reserve)  # release после commit — no-op
        db.commit()
        db.expire_all()
        rows = db.execute(select(BudgetLedger)).scalars().all()
        assert all(float(r.spent_usd) == 0.8 for r in rows)


def test_r04_overrun_recorded_and_blocks_next(env, monkeypatch):
    """Факт > оценки: расход честно записан, overrun помечен, следующий
    вызов блокируется лимитом."""
    c, S = env
    register(c)
    monkeypatch.setattr(providers, "chat", stub_ok(tokens_in=20_000_000))
    body = complete_body(task_budget_max_usd=25)  # дневной cap 15
    r = c.post("/complete", json=body, headers=H_ORCH)
    assert r.status_code == 200, r.text
    assert r.json()["overrun"] is True
    b = c.get("/budget/T", headers=H_ADMIN).json()
    assert b["day"]["spent_usd"] > 15 and b["day"]["overrun"] is True
    r2 = c.post("/complete", json=body, headers=H_ORCH)
    assert r2.status_code == 402
