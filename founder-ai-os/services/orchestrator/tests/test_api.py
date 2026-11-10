"""Штатные тесты API v0.2.1: токены, полный цикл, бюджет, approvals, аудит."""
import json
import os
import uuid

os.environ["ORCHESTRATOR_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ORCHESTRATOR_OWNER_IDS"] = "owner-1"
os.environ["ORCHESTRATOR_TOKENS"] = json.dumps({
    "tok-admin": {"actor": "admin-1", "role": "admin"},
    "tok-orch": {"actor": "orch-1", "role": "orchestrator"},
    "tok-owner": {"actor": "owner-1", "role": "owner"},
    "tok-ci": {"actor": "ci-bot", "role": "ci"},
    "tok-exec": {"actor": "agent-exec", "role": "agent"},
    "tok-rev": {"actor": "agent-rev", "role": "agent"},
})

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

OWNER = "owner-1"
H_ADMIN = {"Authorization": "Bearer tok-admin"}
H_ORCH = {"Authorization": "Bearer tok-orch"}
H_OWNER = {"Authorization": "Bearer tok-owner"}
H_CI = {"Authorization": "Bearer tok-ci"}
H_EXEC = {"Authorization": "Bearer tok-exec"}
H_REV = {"Authorization": "Bearer tok-rev"}

EXEC_ID = "agent-exec"
REV_ID = "agent-rev"
ARTIFACT_V1 = "ab" * 32


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _bootstrap(client):
    tenant = client.post("/tenants", json={"name": "Corp", "slug": "corp"},
                         headers=H_ADMIN).json()
    project = client.post("/projects", json={
        "tenant_id": tenant["id"], "name": "Site"}, headers=H_ADMIN).json()
    client.post("/agents", json={
        "tenant_id": tenant["id"], "role_code": "codex-developer",
        "name": "Codex", "id": EXEC_ID}, headers=H_ADMIN)
    client.post("/agents", json={
        "tenant_id": tenant["id"], "role_code": "claude-developer",
        "name": "Claude", "id": REV_ID}, headers=H_ADMIN)
    return tenant["id"], project["id"], EXEC_ID, REV_ID


def _task_payload(tenant_id, project_id, reviewer_id, **over):
    payload = {
        "tenant_id": tenant_id,
        "project_id": project_id,
        "department": "development",
        "goal": "Добавить /health endpoint в сервис",
        "why": "Healthcheck нужен для deploy-broker и мониторинга uptime",
        "expected_output": {"type": "code_change", "description": "GET /health возвращает 200 ok"},
        "acceptance_criteria": [
            {"type": "command", "description": "pytest зелёный", "command": "pytest -q"},
        ],
        "reviewer": reviewer_id,
        "budget": {"max_usd": 2.0},
    }
    payload.update(over)
    return payload


def _report(task_id, artifact=ARTIFACT_V1, cost=0.1, report=None):
    return {"report": report or {"WHAT_CHANGED": "x"}, "artifact_sha256": artifact,
            "cost_usd": cost}


def _to_running(client, task_id):
    assert client.post(f"/tasks/{task_id}/submit", headers=H_ORCH).status_code == 200
    r = client.post(f"/tasks/{task_id}/claim", json={}, headers=H_EXEC)
    assert r.status_code == 200, r.text


def test_full_cycle(client):
    tenant_id, project_id, executor_id, reviewer_id = _bootstrap(client)

    r = client.post("/tasks", json=_task_payload(tenant_id, project_id, reviewer_id),
                    headers=H_ORCH)
    assert r.status_code == 201, r.text
    task_id = r.json()["task_id"]

    _to_running(client, task_id)

    r = client.post(f"/tasks/{task_id}/report", json=_report(task_id), headers=H_EXEC)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "review"

    # исполнитель не может ревьюить сам себя
    r = client.post(f"/tasks/{task_id}/review",
                    json={"verdict": "approve"}, headers=H_EXEC)
    assert r.status_code in (403, 409)

    r = client.post(f"/tasks/{task_id}/review",
                    json={"verdict": "approve"}, headers=H_REV)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # code_change: без CI-аттестации complete отклоняется
    r = client.post(f"/tasks/{task_id}/complete", json={}, headers=H_ORCH)
    assert r.status_code == 409

    # CI аттестует ДРУГУЮ версию — отказ
    r = client.post(f"/tasks/{task_id}/ci", headers=H_CI, json={
        "passed": True, "evidence": "ci-run-1", "artifact_sha256": "00" * 32})
    assert r.status_code == 409

    # CI аттестует текущую версию
    r = client.post(f"/tasks/{task_id}/ci", headers=H_CI, json={
        "passed": True, "evidence": "ci-run-1", "artifact_sha256": ARTIFACT_V1})
    assert r.status_code == 200

    r = client.post(f"/tasks/{task_id}/complete", json={}, headers=H_ORCH)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"

    r = client.get("/audit/verify", params={"tenant_id": tenant_id}, headers=H_ADMIN)
    assert r.json()["chain_valid"] is True


def test_rework_cycle_and_escalation(client):
    tenant_id, project_id, _, reviewer_id = _bootstrap(client)
    r = client.post("/tasks", json=_task_payload(tenant_id, project_id, reviewer_id),
                    headers=H_ORCH)
    task_id = r.json()["task_id"]
    _to_running(client, task_id)

    for cycle in range(3):
        artifact = f"{cycle:064d}"  # каждая попытка — новая версия
        r = client.post(f"/tasks/{task_id}/report",
                        json=_report(task_id, artifact=artifact), headers=H_EXEC)
        assert r.json()["status"] == "review"
        r = client.post(f"/tasks/{task_id}/review", headers=H_REV, json={
            "verdict": "request_changes",
            "findings": [{"severity": "minor", "issue": "x"}]})
        if cycle < 2:
            assert r.json()["status"] == "rework"
            rc = client.post(f"/tasks/{task_id}/claim", json={}, headers=H_EXEC)
            assert rc.status_code == 200, rc.text
        else:
            assert r.json()["status"] == "blocked"
            assert r.json()["escalated"] is True


def test_claim_only_from_queue(client):
    tenant_id, project_id, _, reviewer_id = _bootstrap(client)
    r = client.post("/tasks", json=_task_payload(tenant_id, project_id, reviewer_id),
                    headers=H_ORCH)
    task_id = r.json()["task_id"]
    r = client.post(f"/tasks/{task_id}/claim", json={}, headers=H_EXEC)
    assert r.status_code == 409


def test_schema_rejects_no_why(client):
    tenant_id, project_id, _, reviewer_id = _bootstrap(client)
    payload = _task_payload(tenant_id, project_id, reviewer_id)
    del payload["why"]
    r = client.post("/tasks", json=payload, headers=H_ORCH)
    assert r.status_code == 422


def test_budget_required(client):
    tenant_id, project_id, _, reviewer_id = _bootstrap(client)
    r = client.post("/tasks", json=_task_payload(
        tenant_id, project_id, reviewer_id, budget={"max_usd": None}), headers=H_ORCH)
    assert r.status_code == 422


def test_executor_cannot_be_reviewer(client):
    tenant_id, project_id, executor_id, _ = _bootstrap(client)
    r = client.post("/tasks", json=_task_payload(
        tenant_id, project_id, reviewer_id=executor_id), headers=H_ORCH)
    task_id = r.json()["task_id"]
    _to_running(client, task_id)
    r = client.post(f"/tasks/{task_id}/report", json=_report(task_id), headers=H_EXEC)
    assert r.status_code == 409  # закон 3


def test_budget_exceeded_blocks(client):
    tenant_id, project_id, _, reviewer_id = _bootstrap(client)
    r = client.post("/tasks", json=_task_payload(
        tenant_id, project_id, reviewer_id, budget={"max_usd": 0.5}), headers=H_ORCH)
    task_id = r.json()["task_id"]
    _to_running(client, task_id)
    r = client.post(f"/tasks/{task_id}/report",
                    json=_report(task_id, cost=1.0), headers=H_EXEC)
    assert r.json()["status"] == "blocked"


def test_approval_flow(client):
    tenant_id, *_ = _bootstrap(client)
    r = client.post("/approvals", headers=H_ORCH, json={
        "tenant_id": tenant_id, "type": "high_risk_deploy",
        "payload": {"commit": "abc123"}})
    approval_id = r.json()["approval_id"]
    assert r.json()["expires_at"]

    r = client.post(f"/approvals/{approval_id}/decide",
                    json={"decision": "approved"}, headers=H_OWNER)
    assert r.json()["status"] == "approved"

    # повторное решение запрещено
    r = client.post(f"/approvals/{approval_id}/decide",
                    json={"decision": "rejected"}, headers=H_OWNER)
    assert r.status_code == 409

    # не-owner токен не может решать
    r2 = client.post("/approvals", headers=H_ORCH,
                     json={"tenant_id": tenant_id, "type": "payment"})
    r = client.post(f"/approvals/{r2.json()['approval_id']}/decide",
                    json={"decision": "approved"}, headers=H_EXEC)
    assert r.status_code == 403


def test_unknown_tenant_rejected(client):
    r = client.post("/tasks", json=_task_payload(
        str(uuid.uuid4()), str(uuid.uuid4()), REV_ID), headers=H_ORCH)
    assert r.status_code == 404


def test_cancel_only_owner(client):
    tenant_id, project_id, _, reviewer_id = _bootstrap(client)
    r = client.post("/tasks", json=_task_payload(tenant_id, project_id, reviewer_id),
                    headers=H_ORCH)
    task_id = r.json()["task_id"]
    r = client.post(f"/tasks/{task_id}/cancel", json={}, headers=H_EXEC)
    assert r.status_code == 403
    r = client.post(f"/tasks/{task_id}/cancel", json={}, headers=H_OWNER)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_report_requires_artifact_hash(client):
    tenant_id, project_id, _, reviewer_id = _bootstrap(client)
    r = client.post("/tasks", json=_task_payload(tenant_id, project_id, reviewer_id),
                    headers=H_ORCH)
    task_id = r.json()["task_id"]
    _to_running(client, task_id)
    r = client.post(f"/tasks/{task_id}/report", headers=H_EXEC,
                    json={"report": {}, "cost_usd": 0.1})
    assert r.status_code == 422  # R-02: версия артефакта обязательна
