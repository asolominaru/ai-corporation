"""Регрессии независимых проверок. N-01..N-05 — 2026-11-05,
R-01/R-02 — 2026-11-06 (test_orchestrator_20261106.py). Все сценарии
ожидают БЕЗОПАСНЫЙ ОТКАЗ там, где проверка воспроизвела дефект."""
import os
from datetime import datetime, timezone, timedelta

os.environ["ORCHESTRATOR_DATABASE_URL"] = "sqlite:///:memory:"

from test_api import (  # noqa: E402
    client, _bootstrap, _task_payload, _to_running, _report,
    OWNER, H_ADMIN, H_ORCH, H_OWNER, H_CI, H_EXEC, H_REV,
    EXEC_ID, REV_ID, ARTIFACT_V1,
)
from app.main import app  # noqa: E402
from app.db import get_db  # noqa: E402
from app.models import AuditLog, Approval  # noqa: E402
from sqlalchemy import select  # noqa: E402


def _db_session():
    gen = app.dependency_overrides[get_db]()
    return gen, next(gen)


# --- N-01: нет произвольных переходов; complete требует фактов ----------------

def test_n01_cannot_complete_without_facts(client):
    t, p, e, r = _bootstrap(client)
    task = client.post("/tasks", json=_task_payload(
        t, p, r, requires_human_approval=["high_risk_deploy"]),
        headers=H_ORCH).json()["task_id"]

    assert client.post(f"/tasks/{task}/transition", json={
        "to": "queued"}, headers=H_ORCH).status_code in (404, 405)
    assert client.post(f"/tasks/{task}/claim", json={}, headers=H_EXEC).status_code == 409

    client.post(f"/tasks/{task}/submit", headers=H_ORCH)
    assert client.post(f"/tasks/{task}/report", json=_report(task),
                       headers=H_EXEC).status_code == 409

    client.post(f"/tasks/{task}/claim", json={}, headers=H_EXEC)
    client.post(f"/tasks/{task}/report", json=_report(task), headers=H_EXEC)

    assert client.post(f"/tasks/{task}/review", json={"verdict": "approve"},
                       headers=H_EXEC).status_code in (403, 409)
    assert client.post(f"/tasks/{task}/review", json={"verdict": "approve"},
                       headers=H_REV).status_code == 200

    # нет CI → нет complete
    assert client.post(f"/tasks/{task}/complete", json={},
                       headers=H_ORCH).status_code == 409
    client.post(f"/tasks/{task}/ci", headers=H_CI, json={
        "passed": True, "evidence": "run-1", "artifact_sha256": ARTIFACT_V1})

    # нет owner approval → нет complete
    assert client.post(f"/tasks/{task}/complete", json={},
                       headers=H_ORCH).status_code == 409

    # approval на другую версию → complete отклонён
    aid = client.post("/approvals", headers=H_ORCH, json={
        "tenant_id": t, "task_id": task, "type": "high_risk_deploy",
        "payload": {"artifact_sha256": "00" * 32}}).json()["approval_id"]
    client.post(f"/approvals/{aid}/decide", json={"decision": "approved"},
                headers=H_OWNER)
    assert client.post(f"/tasks/{task}/complete", json={},
                       headers=H_ORCH).status_code == 409

    # approval на текущую версию → complete проходит
    aid2 = client.post("/approvals", headers=H_ORCH, json={
        "tenant_id": t, "task_id": task, "type": "high_risk_deploy",
        "payload": {"artifact_sha256": ARTIFACT_V1}}).json()["approval_id"]
    client.post(f"/approvals/{aid2}/decide", json={"decision": "approved"},
                headers=H_OWNER)
    res = client.post(f"/tasks/{task}/complete", json={}, headers=H_ORCH)
    assert res.status_code == 200, res.text


# --- N-02: tenant-изоляция ----------------------------------------------------

def test_n02_cross_tenant_rejected(client):
    t, p, e, r = _bootstrap(client)
    other = client.post("/tenants", json={"name": "Other", "slug": "other"},
                        headers=H_ADMIN).json()["id"]

    assert client.post("/tasks", json=_task_payload(other, p, r),
                       headers=H_ORCH).status_code == 422

    client.post("/agents", json={
        "tenant_id": other, "role_code": "reviewer-auditor",
        "name": "Ext", "id": "agent-ext"}, headers=H_ADMIN)
    assert client.post("/tasks", json=_task_payload(t, p, "agent-ext"),
                       headers=H_ORCH).status_code == 422

    task = client.post("/tasks", json=_task_payload(t, p, r),
                       headers=H_ORCH).json()["task_id"]
    client.post(f"/tasks/{task}/submit", headers=H_ORCH)
    # агент чужого tenant (токен не выпущен) → 401; чужой id в теле → 403
    assert client.post(f"/tasks/{task}/claim", json={}).status_code == 401
    assert client.post(f"/tasks/{task}/claim", json={"agent_id": "agent-ext"},
                       headers=H_EXEC).status_code == 403


# --- N-03: бюджет -------------------------------------------------------------

def test_n03_negative_cost_rejected(client):
    t, p, e, r = _bootstrap(client)
    task = client.post("/tasks", json=_task_payload(t, p, r),
                       headers=H_ORCH).json()["task_id"]
    _to_running(client, task)
    res = client.post(f"/tasks/{task}/report", headers=H_EXEC, json={
        "report": {}, "artifact_sha256": ARTIFACT_V1,
        "cost_usd": -100, "tokens_in": -10})
    assert res.status_code == 422


def test_n03_cumulative_budget_blocks(client):
    t, p, e, r = _bootstrap(client)
    task = client.post("/tasks", json=_task_payload(
        t, p, r, budget={"max_usd": 0.5}), headers=H_ORCH).json()["task_id"]
    _to_running(client, task)
    res = client.post(f"/tasks/{task}/report",
                      json=_report(task, artifact="aa" * 32, cost=0.4), headers=H_EXEC)
    assert res.json()["status"] == "review"

    client.post(f"/tasks/{task}/review", headers=H_REV, json={
        "verdict": "request_changes", "findings": []})
    client.post(f"/tasks/{task}/claim", json={}, headers=H_EXEC)
    res = client.post(f"/tasks/{task}/report",
                      json=_report(task, artifact="bb" * 32, cost=0.4), headers=H_EXEC)
    assert res.json()["status"] == "blocked"  # 0.8 > 0.5 по сумме попыток

    client.post(f"/tasks/{task}/requeue", json={}, headers=H_OWNER)
    assert client.post(f"/tasks/{task}/claim", json={},
                       headers=H_EXEC).status_code == 409


# --- N-04: approvals ----------------------------------------------------------

def test_n04_expired_and_unverified_decisions_rejected(client):
    t, *_ = _bootstrap(client)
    aid = client.post("/approvals", headers=H_ORCH, json={
        "tenant_id": t, "type": "high_risk_deploy"}).json()["approval_id"]

    # без токена — 401, даже с owner id в теле
    assert client.post(f"/approvals/{aid}/decide", json={
        "decision": "approved", "decided_by": OWNER}).status_code == 401
    # чужой токен — 403
    assert client.post(f"/approvals/{aid}/decide", json={"decision": "approved"},
                       headers=H_EXEC).status_code == 403

    # просроченный — 409
    gen, db = _db_session()
    try:
        db.get(Approval, aid).expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    finally:
        gen.close()
    assert client.post(f"/approvals/{aid}/decide", json={"decision": "approved"},
                       headers=H_OWNER).status_code == 409


# --- N-05: аудит ---------------------------------------------------------------

def test_n05_audit_tamper_detected(client):
    t, p, e, r = _bootstrap(client)
    client.post("/tasks", json=_task_payload(t, p, r), headers=H_ORCH)
    assert client.get("/audit/verify", params={"tenant_id": t},
                      headers=H_ADMIN).json()["chain_valid"]

    gen, db = _db_session()
    try:
        row = db.execute(
            select(AuditLog).where(AuditLog.tenant_id == t)).scalars().first()
        row.actor_id = "changed-actor"
        row.action = "changed-action"
        db.commit()
    finally:
        gen.close()
    assert client.get("/audit/verify", params={"tenant_id": t},
                      headers=H_ADMIN).json()["chain_valid"] is False


# --- R-01: подставленная личность и выдуманный CI ------------------------------

def test_r01_no_token_no_power(client):
    """Сценарий проверки: без заголовков auth запросы с 'правильными'
    именами owner/reviewer и выдуманным CI доводили задачу до completed.
    Теперь каждый шаг без токена → 401, с чужим токеном → 403."""
    t, p, e, r = _bootstrap(client)
    task = client.post("/tasks", json=_task_payload(
        t, p, r, requires_human_approval=["high_risk_deploy"]),
        headers=H_ORCH).json()["task_id"]

    assert client.post(f"/tasks/{task}/submit").status_code == 401
    client.post(f"/tasks/{task}/submit", headers=H_ORCH)

    assert client.post(f"/tasks/{task}/claim", json={"agent_id": e}).status_code == 401
    client.post(f"/tasks/{task}/claim", json={}, headers=H_EXEC)

    assert client.post(f"/tasks/{task}/report", json=_report(task)).status_code == 401
    client.post(f"/tasks/{task}/report", json=_report(task), headers=H_EXEC)

    # reviewer по телу без токена — 401; токеном исполнителя — 403/409
    assert client.post(f"/tasks/{task}/review", json={
        "reviewer_id": r, "verdict": "approve"}).status_code == 401
    assert client.post(f"/tasks/{task}/review", json={"verdict": "approve"},
                       headers=H_EXEC).status_code in (403, 409)
    client.post(f"/tasks/{task}/review", json={"verdict": "approve"}, headers=H_REV)

    # CI-аттестация не-agent/не-orchestrator токеном — 403; owner не CI
    assert client.post(f"/tasks/{task}/ci", headers=H_OWNER, json={
        "passed": True, "evidence": "fake-ci-run", "artifact_sha256": ARTIFACT_V1}
        ).status_code == 403
    # complete без реальной аттестации роли ci — 409
    assert client.post(f"/tasks/{task}/complete", json={
        "ci_passed": True, "ci_evidence": "invented-not-a-CI-run"},
        headers=H_ORCH).status_code == 409

    # owner-решение без токена — 401
    aid = client.post("/approvals", headers=H_ORCH, json={
        "tenant_id": t, "task_id": task, "type": "high_risk_deploy",
        "payload": {"artifact_sha256": ARTIFACT_V1}}).json()["approval_id"]
    assert client.post(f"/approvals/{aid}/decide", json={
        "decision": "approved", "decided_by": OWNER}).status_code == 401
    assert client.get(f"/tasks/{task}").status_code == 401


# --- R-02: версия артефакта обязательна и привязана ----------------------------

def test_r02_no_hash_no_progress(client):
    """Отчёт без artifact_sha256 отклоняется; complete без версии невозможен."""
    t, p, e, r = _bootstrap(client)
    task = client.post("/tasks", json=_task_payload(
        t, p, r, requires_human_approval=["high_risk_deploy"]),
        headers=H_ORCH).json()["task_id"]
    _to_running(client, task)
    assert client.post(f"/tasks/{task}/report", headers=H_EXEC,
                       json={"report": {}, "cost_usd": 0.1}).status_code == 422


def test_r02_rework_requires_new_approval_for_new_version(client):
    """Approval версии A не действует на версию B после rework."""
    t, p, e, r = _bootstrap(client)
    task = client.post("/tasks", json=_task_payload(
        t, p, r, requires_human_approval=["high_risk_deploy"]),
        headers=H_ORCH).json()["task_id"]
    _to_running(client, task)
    client.post(f"/tasks/{task}/report",
                json=_report(task, artifact="aa" * 32), headers=H_EXEC)

    aid = client.post("/approvals", headers=H_ORCH, json={
        "tenant_id": t, "task_id": task, "type": "high_risk_deploy",
        "payload": {"artifact_sha256": "aa" * 32}}).json()["approval_id"]
    client.post(f"/approvals/{aid}/decide", json={"decision": "approved"},
                headers=H_OWNER)

    client.post(f"/tasks/{task}/review", headers=H_REV, json={
        "verdict": "request_changes", "findings": []})
    client.post(f"/tasks/{task}/claim", json={}, headers=H_EXEC)
    client.post(f"/tasks/{task}/report",
                json=_report(task, artifact="bb" * 32), headers=H_EXEC)  # новая версия
    client.post(f"/tasks/{task}/review", json={"verdict": "approve"}, headers=H_REV)
    client.post(f"/tasks/{task}/ci", headers=H_CI, json={
        "passed": True, "evidence": "run-2", "artifact_sha256": "bb" * 32})

    # старый approval (версия aa) к версии bb не привязан → отказ
    res = client.post(f"/tasks/{task}/complete", json={}, headers=H_ORCH)
    assert res.status_code == 409, res.text
