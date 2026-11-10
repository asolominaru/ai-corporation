"""Orchestrator API (0.3.0 — п.3 повторной проверки: Telegram-мост, артефакты).

Личность и полномочия определяются service token'ом (app/auth.py),
а не полями JSON-тела. Нет токена — 401, даже с «правильным» owner id.

Эндпоинты (роль → действие):
- GET  /health                                  — публичный
- POST /tenants, /projects, /agents             — admin
- POST /tasks                                   — orchestrator/admin
- POST /tasks/{id}/submit                       — orchestrator/admin
- POST /tasks/{id}/claim                        — agent (claim только «за себя»)
- POST /tasks/{id}/report                       — agent (только свой активный run;
                                                  artifact_text кладётся в
                                                  content-addressed хранилище)
- POST /tasks/{id}/review                       — agent, actor == назначенный reviewer
- POST /tasks/{id}/ci                           — ci: аттестация CI по версии артефакта
- POST /tasks/{id}/complete                     — orchestrator (факты: run+report+
                                                  review+CI+owner approval на версию)
- POST /tasks/{id}/cancel, /requeue             — owner (∈ OWNER_IDS)
- POST /approvals                               — orchestrator/admin (+ публикация
                                                  в Telegram-мост, если он включён)
- POST /approvals/{id}/decide                   — owner, атомарно, один раз, до expiry
- POST /bridge/sync                             — orchestrator: решения из реестра
                                                  approval-бота → approvals
- GET  /tasks, /tasks/{id}, /audit/verify       — любой валидный токен (tenant-scope)
"""
import hashlib
import math
import re
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from .auth import Actor, require_auth, require_role, check_tenant_scope
from .config import (
    OWNER_IDS, APPROVAL_TTL_HOURS, APPROVAL_REGISTRY_PATH, ARTIFACT_DIR,
)
from .db import Base, engine, get_db
from .models import (
    Tenant, Project, Agent, Task, TaskRun, Approval, utcnow, aware,
)
from .statemachine import check_transition, TransitionError, TaskStatus
from .audit import audit, verify_chain
from .taskschema import validate_task_payload, TaskValidationError
from . import bridge

MAX_REWORK_CYCLES = 2  # TASK_PROTOCOL §3: ≤2 циклов, затем эскалация
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev: create_all. Prod: Alembic-миграции, create_all не используется.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Founder AI OS — Orchestrator", version="0.3.0", lifespan=lifespan)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(func.now()))  # не static-ok: БД обязана отвечать
    return {"status": "ok", "service": "orchestrator", "version": "0.3.0"}


# --- Helpers -----------------------------------------------------------------

def _get_task(db: Session, task_id: str) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task не найдена")
    return task


def _get_agent_same_tenant(db: Session, agent_id: str, tenant_id: str) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "agent не найден")
    if agent.tenant_id != tenant_id:
        raise HTTPException(403, "agent принадлежит другому tenant")
    return agent


def _spent_usd(db: Session, task_id: str) -> float:
    total = db.execute(
        select(func.coalesce(func.sum(TaskRun.cost_usd), 0))
        .where(TaskRun.task_id == task_id)
    ).scalar()
    return float(total)


def _require_owner(actor: Actor):
    require_role(actor, "owner")
    if actor.actor_id not in OWNER_IDS:
        raise HTTPException(403, "токен владельца не входит в OWNER_IDS")


def _store_artifact(sha256: str, text: str) -> str:
    """Content-addressed хранилище: файл назван хешем содержимого.
    Несовпадение хеша — отказ до записи (сценарий «материал изменён»)."""
    actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if actual != sha256:
        raise HTTPException(
            422, "artifact_text не соответствует artifact_sha256: "
                 "либо подменено содержимое, либо неверен хеш")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / sha256
    if not path.exists():
        tmp = ARTIFACT_DIR / (sha256 + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    return str(path)


def _do_transition(db: Session, task: Task, target: str, *, actor_type: str,
                   actor_id: str, action: str, ci_passed=None, extra=None):
    """Единственная точка смены статуса: state machine + аудит."""
    out_type = (task.expected_output or {}).get("type")
    try:
        new_status = check_transition(
            task.status, target, actor_type=actor_type,
            expected_output_type=out_type, ci_passed=ci_passed,
        )
    except TransitionError as e:
        raise HTTPException(409, str(e)) from e
    old = task.status
    task.status = new_status.value
    payload = {"from": old, "to": new_status.value}
    if extra:
        payload.update(extra)
    audit(db, tenant_id=task.tenant_id, actor_type=actor_type, actor_id=actor_id,
          action=action, entity_type="task", entity_id=task.id, payload=payload)
    return old, new_status.value


def _task_out(t: Task) -> dict:
    return {
        "task_id": t.id, "tenant_id": t.tenant_id, "project_id": t.project_id,
        "department": t.department, "goal": t.goal, "status": t.status,
        "mode": t.mode, "reviewer": t.reviewer, "budget": t.budget,
        "artifact_sha256": t.artifact_sha256, "rework_count": t.rework_count,
        "ci_passed": t.ci_passed, "ci_evidence": t.ci_evidence,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


# --- Dev bootstrap (admin) ---------------------------------------------------

class TenantIn(BaseModel):
    name: str
    slug: str


class ProjectIn(BaseModel):
    tenant_id: str
    name: str
    repo_url: str | None = None


class AgentIn(BaseModel):
    tenant_id: str
    role_code: str
    name: str
    id: str | None = None  # фиксированный id для привязки service token'а
    tools: list[str] = []
    permissions: list[str] = []
    reviewer_agent_id: str | None = None


@app.post("/tenants", status_code=201)
def create_tenant(body: TenantIn, db: Session = Depends(get_db),
                  actor: Actor = Depends(require_auth)):
    require_role(actor, "admin")
    t = Tenant(name=body.name, slug=body.slug)
    db.add(t)
    db.commit()
    return {"id": t.id, "slug": t.slug}


@app.post("/projects", status_code=201)
def create_project(body: ProjectIn, db: Session = Depends(get_db),
                   actor: Actor = Depends(require_auth)):
    require_role(actor, "admin")
    if not db.get(Tenant, body.tenant_id):
        raise HTTPException(404, "tenant не найден")
    p = Project(**body.model_dump())
    db.add(p)
    db.commit()
    return {"id": p.id}


@app.post("/agents", status_code=201)
def create_agent(body: AgentIn, db: Session = Depends(get_db),
                 actor: Actor = Depends(require_auth)):
    require_role(actor, "admin")
    if not db.get(Tenant, body.tenant_id):
        raise HTTPException(404, "tenant не найден")
    a = Agent(**body.model_dump())
    db.add(a)
    db.commit()
    return {"id": a.id}


# --- Tasks -------------------------------------------------------------------

@app.post("/tasks", status_code=201)
def create_task(payload: dict, db: Session = Depends(get_db),
                actor: Actor = Depends(require_auth)):
    require_role(actor, "orchestrator", "admin")
    try:
        data = validate_task_payload(payload)
    except TaskValidationError as e:
        raise HTTPException(422, str(e)) from e

    tenant = db.get(Tenant, data["tenant_id"])
    if not tenant:
        raise HTTPException(404, "tenant не найден")
    check_tenant_scope(actor, tenant.id)
    project = db.get(Project, data["project_id"])
    if not project:
        raise HTTPException(404, "project не найден")
    if project.tenant_id != tenant.id:
        raise HTTPException(422, "project_id принадлежит другому tenant")

    reviewer_agent = db.get(Agent, data["reviewer"])
    if reviewer_agent is not None and reviewer_agent.tenant_id != tenant.id:
        raise HTTPException(422, "reviewer принадлежит другому tenant")

    task = Task(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        project_id=project.id,
        department=data["department"],
        workflow_run_id=data.get("workflow_run_id"),
        parent_task_id=data.get("parent_task_id"),
        goal=data["goal"],
        why=data["why"],
        input=data.get("input", {}),
        context=data.get("context", {}),
        expected_output=data["expected_output"],
        acceptance_criteria=data["acceptance_criteria"],
        tools_allowed=data.get("tools_allowed", []),
        permissions=data.get("permissions", []),
        mode=data.get("mode", "REVIEW"),
        primary_model=data.get("primary_model"),
        fallback_model=data.get("fallback_model"),
        budget=data["budget"],
        deadline=data.get("deadline"),
        reviewer=data["reviewer"],
        retry_policy=data.get("retry_policy", {"max_attempts": 2, "backoff_seconds": 300}),
        escalation_policy=data.get("escalation_policy", {}),
        requires_human_approval=data.get("requires_human_approval", []),
        next_action=data.get("next_action"),
        status=TaskStatus.CREATED.value,
    )
    db.add(task)
    audit(db, tenant_id=task.tenant_id, actor_type="orchestrator", actor_id=actor.actor_id,
          action="task.created", entity_type="task", entity_id=task.id,
          payload={"goal": task.goal, "budget": task.budget})
    db.commit()
    return {"task_id": task.id, "status": task.status}


@app.get("/tasks")
def list_tasks(tenant_id: str = Query(...), status: str | None = None,
               db: Session = Depends(get_db), actor: Actor = Depends(require_auth)):
    check_tenant_scope(actor, tenant_id)
    q = select(Task).where(Task.tenant_id == tenant_id)
    if status:
        q = q.where(Task.status == status)
    return [_task_out(t) for t in db.execute(q).scalars().all()]


@app.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db),
             actor: Actor = Depends(require_auth)):
    t = _get_task(db, task_id)
    check_tenant_scope(actor, t.tenant_id)
    out = _task_out(t)
    out["spent_usd"] = _spent_usd(db, t.id)
    return out


@app.post("/tasks/{task_id}/submit")
def submit_task(task_id: str, db: Session = Depends(get_db),
                actor: Actor = Depends(require_auth)):
    require_role(actor, "orchestrator", "admin")
    task = _get_task(db, task_id)
    check_tenant_scope(actor, task.tenant_id)
    _do_transition(db, task, "queued", actor_type="orchestrator",
                   actor_id=actor.actor_id, action="task.submitted")
    db.commit()
    return {"task_id": task.id, "status": task.status}


class ClaimIn(BaseModel):
    agent_id: str | None = None  # если задан — обязан совпадать с токеном


@app.post("/tasks/{task_id}/claim")
def claim_task(task_id: str, body: ClaimIn, db: Session = Depends(get_db),
               actor: Actor = Depends(require_auth)):
    """Агент забирает задачу СЕБЕ: личность — из токена, не из тела (R-01).
    Postgres-версия очереди — SELECT ... FOR UPDATE SKIP LOCKED."""
    require_role(actor, "agent")
    task = _get_task(db, task_id)
    check_tenant_scope(actor, task.tenant_id)
    if body.agent_id and body.agent_id != actor.actor_id:
        raise HTTPException(403, "claim возможен только за себя (токен ≠ agent_id)")
    agent = _get_agent_same_tenant(db, actor.actor_id, task.tenant_id)

    # Бюджет проверяется ДО начала работы по накопленным тратам (N-03).
    max_usd = float((task.budget or {}).get("max_usd") or 0)
    spent = _spent_usd(db, task.id)
    if max_usd and spent >= max_usd:
        if task.status != TaskStatus.BLOCKED.value:
            task.status = TaskStatus.BLOCKED.value
            audit(db, tenant_id=task.tenant_id, actor_type="orchestrator",
                  actor_id="budget-guard", action="task.budget_exceeded",
                  entity_type="task", entity_id=task.id,
                  payload={"spent": spent, "max_usd": max_usd})
            db.commit()
        raise HTTPException(409, f"бюджет исчерпан: {spent:.4f} >= {max_usd}")

    try:
        check_transition(task.status, "running", actor_type="agent")
    except TransitionError as e:
        raise HTTPException(409, str(e)) from e
    old = task.status
    task.status = TaskStatus.RUNNING.value

    attempt = db.execute(
        select(func.count(TaskRun.id)).where(TaskRun.task_id == task_id)
    ).scalar() + 1
    run = TaskRun(
        tenant_id=task.tenant_id, task_id=task.id, agent_id=agent.id,
        mode=task.mode, attempt=attempt,
        branch=f"task/{task.id[:8]}-{agent.id[:8]}",
    )
    db.add(run)
    audit(db, tenant_id=task.tenant_id, actor_type="agent",
          actor_id=agent.id, action="task.claimed",
          entity_type="task", entity_id=task.id,
          payload={"from": old, "to": task.status, "agent_id": agent.id,
                   "attempt": attempt})
    db.commit()
    return {"run_id": run.id, "attempt": attempt, "status": task.status}


class ReportIn(BaseModel):
    report: dict  # WHAT_CHANGED/FILES_CHANGED/TEST_RESULTS/RISKS/KNOWN_ISSUES/NEXT_STEP
    artifact_sha256: str  # R-02: обязателен — версия результата, к которой всё привязано
    artifact_text: str | None = None  # содержимое артефакта; хеш обязан совпасть
    cost_usd: float = 0
    tokens_in: int = 0
    tokens_out: int = 0
    commit_sha: str | None = None

    @field_validator("artifact_sha256")
    @classmethod
    def _hash_format(cls, v):
        if not SHA256_RE.match(v or ""):
            raise ValueError("artifact_sha256: 64 hex-символа sha256 версии артефакта")
        return v

    @field_validator("cost_usd", "tokens_in", "tokens_out")
    @classmethod
    def _non_negative_finite(cls, v):
        if not math.isfinite(v) or v < 0:
            raise ValueError("cost/tokens должны быть конечными и неотрицательными")
        return v


@app.post("/tasks/{task_id}/report")
def submit_report(task_id: str, body: ReportIn, db: Session = Depends(get_db),
                  actor: Actor = Depends(require_auth)):
    """Агент сдаёт report.json. Личность — из токена (R-01). Новый отчёт —
    новая версия артефакта: прежние review/approval к ней не привязаны (R-02)."""
    require_role(actor, "agent")
    task = _get_task(db, task_id)
    check_tenant_scope(actor, task.tenant_id)
    if actor.actor_id == task.reviewer:
        raise HTTPException(409, "исполнитель не может быть reviewer'ом (закон 3)")
    _get_agent_same_tenant(db, actor.actor_id, task.tenant_id)

    run = db.execute(
        select(TaskRun)
        .where(TaskRun.task_id == task_id, TaskRun.agent_id == actor.actor_id,
               TaskRun.status == "running")
        .order_by(TaskRun.started_at.desc())
    ).scalars().first()
    if not run:
        raise HTTPException(409, "нет активного run для этого агента")
    if task.status != TaskStatus.RUNNING.value:
        raise HTTPException(409, f"задача в статусе {task.status}, отчёт не принимается")

    artifact_path = None
    if body.artifact_text is not None:
        artifact_path = _store_artifact(body.artifact_sha256, body.artifact_text)

    spent_before = _spent_usd(db, task.id)  # до записи стоимости run (N-03)

    run.status = "done"
    run.finished_at = utcnow()
    run.report = body.report
    run.cost_usd = body.cost_usd
    run.tokens_in = body.tokens_in
    run.tokens_out = body.tokens_out
    run.commit_sha = body.commit_sha
    # Новая версия артефакта; прежняя CI-аттестация к ней не относится.
    task.artifact_sha256 = body.artifact_sha256
    task.ci_passed = None
    task.ci_evidence = None
    task.ci_at = None

    max_usd = float((task.budget or {}).get("max_usd") or 0)
    total = spent_before + float(body.cost_usd)
    if max_usd and total > max_usd:
        task.status = TaskStatus.BLOCKED.value
        audit(db, tenant_id=task.tenant_id, actor_type="orchestrator",
              actor_id="budget-guard", action="task.budget_exceeded",
              entity_type="task", entity_id=task.id,
              payload={"spent": total, "max_usd": max_usd})
    else:
        _do_transition(db, task, "review", actor_type="agent",
                       actor_id=actor.actor_id, action="task.report_submitted",
                       extra={"run_id": run.id, "cost_usd": body.cost_usd,
                              "artifact_sha256": body.artifact_sha256})
    db.commit()
    return {"status": task.status, "spent_usd": total,
            "artifact_sha256": task.artifact_sha256,
            "artifact_stored": artifact_path is not None}


class ReviewIn(BaseModel):
    verdict: str = Field(pattern="^(approve|request_changes)$")
    findings: list[dict] = []


@app.post("/tasks/{task_id}/review")
def review_task(task_id: str, body: ReviewIn, db: Session = Depends(get_db),
                actor: Actor = Depends(require_auth)):
    """Вердикт НАЗНАЗЕННОГО reviewer'а; личность — из токена (R-01)."""
    require_role(actor, "agent")
    task = _get_task(db, task_id)
    check_tenant_scope(actor, task.tenant_id)
    if task.status != TaskStatus.REVIEW.value:
        raise HTTPException(409, f"задача не в review (сейчас {task.status})")
    if actor.actor_id != task.reviewer:
        raise HTTPException(403, "review может делать только назначенный reviewer")

    last_run = db.execute(
        select(TaskRun).where(TaskRun.task_id == task_id)
        .order_by(TaskRun.started_at.desc())
    ).scalars().first()
    if last_run and last_run.agent_id == actor.actor_id:
        raise HTTPException(409, "reviewer совпадает с исполнителем (закон 3)")

    if body.verdict == "approve":
        bad = [f for f in body.findings if f.get("severity") in ("blocker", "major")]
        if bad:
            raise HTTPException(422, "approve невозможен при findings blocker/major")
        _do_transition(db, task, "approved", actor_type="agent",
                       actor_id=actor.actor_id, action="task.review_approved",
                       extra={"artifact_sha256": task.artifact_sha256})
    else:
        if task.rework_count >= MAX_REWORK_CYCLES:
            task.status = TaskStatus.BLOCKED.value
            audit(db, tenant_id=task.tenant_id, actor_type="orchestrator",
                  actor_id="api", action="task.rework_limit_escalated",
                  entity_type="task", entity_id=task.id,
                  payload={"rework_count": task.rework_count,
                           "escalate_to": (task.escalation_policy or {}).get("escalate_to")})
            db.commit()
            return {"status": task.status, "escalated": True}
        task.rework_count += 1
        _do_transition(db, task, "rework", actor_type="agent",
                       actor_id=actor.actor_id, action="task.review_changes",
                       extra={"findings": body.findings})
    db.commit()
    return {"status": task.status, "rework_count": task.rework_count}


class CiIn(BaseModel):
    passed: bool
    evidence: str = Field(min_length=5)  # ссылка на прогон CI (run url / log ref)
    artifact_sha256: str  # CI обязан относиться к конкретной версии (R-02)


@app.post("/tasks/{task_id}/ci")
def attest_ci(task_id: str, body: CiIn, db: Session = Depends(get_db),
              actor: Actor = Depends(require_auth)):
    """CI-аттестацию ставит только токен роли ci (R-01). Хеш версии обязан
    совпадать с текущей версией артефакта — иначе аттестация отклоняется."""
    require_role(actor, "ci")
    task = _get_task(db, task_id)
    check_tenant_scope(actor, task.tenant_id)
    if task.artifact_sha256 and body.artifact_sha256 != task.artifact_sha256:
        raise HTTPException(409, "CI относится к другой версии артефакта")
    task.ci_passed = body.passed
    task.ci_evidence = body.evidence
    task.ci_at = utcnow()
    audit(db, tenant_id=task.tenant_id, actor_type="orchestrator",
          actor_id=actor.actor_id, action="task.ci_attested",
          entity_type="task", entity_id=task.id,
          payload={"passed": body.passed, "evidence": body.evidence,
                   "artifact_sha256": body.artifact_sha256})
    db.commit()
    return {"task_id": task.id, "ci_passed": task.ci_passed}


class CompleteIn(BaseModel):
    reason: str | None = None


@app.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, body: CompleteIn, db: Session = Depends(get_db),
                  actor: Actor = Depends(require_auth)):
    """approved → completed. Требуются ФАКТЫ (N-01, R-01, R-02):
    - был task_run и сданный report;
    - версия результата известна (artifact_sha256);
    - для code_change/deployment — CI-аттестация роли ci на ЭТУ версию;
    - для requires_human_approval — действующий approved Approval того типа,
      решённый owner'ом, привязанный к sha256 ТЕКУЩЕЙ версии артефакта.
    """
    require_role(actor, "orchestrator")
    task = _get_task(db, task_id)
    check_tenant_scope(actor, task.tenant_id)

    has_run = db.execute(
        select(func.count(TaskRun.id)).where(TaskRun.task_id == task_id)
    ).scalar()
    if not has_run:
        raise HTTPException(409, "задача не исполнялась: нет ни одного task_run")
    if not task.artifact_sha256:
        raise HTTPException(409, "нет версии результата (artifact_sha256)")

    out_type = (task.expected_output or {}).get("type")
    if out_type in ("code_change", "deployment"):
        if task.ci_passed is not True or not task.ci_evidence:
            raise HTTPException(409, "нет CI-аттестации текущей версии")

    now = utcnow()
    for req in (task.requires_human_approval or []):
        approvals = db.execute(
            select(Approval).where(
                Approval.task_id == task.id, Approval.type == req,
                Approval.status == "approved")
        ).scalars().all()
        valid = [
            a for a in approvals
            if (a.expires_at is None or aware(a.expires_at) > now)
            and a.decided_by in OWNER_IDS
            and (a.payload or {}).get("artifact_sha256") == task.artifact_sha256
        ]
        if not valid:
            raise HTTPException(
                409, f"нет действующего owner approval типа '{req}' "
                     f"на текущую версию артефакта")

    _do_transition(db, task, "completed", actor_type="orchestrator",
                   actor_id=actor.actor_id, action="task.completed",
                   ci_passed=task.ci_passed,
                   extra={"ci_evidence": task.ci_evidence,
                          "artifact_sha256": task.artifact_sha256})
    db.commit()
    return {"task_id": task.id, "status": task.status}


class OwnerActionIn(BaseModel):
    reason: str | None = None


@app.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, body: OwnerActionIn, db: Session = Depends(get_db),
                actor: Actor = Depends(require_auth)):
    """cancelled — только владелец (токен роли owner ∈ OWNER_IDS)."""
    _require_owner(actor)
    task = _get_task(db, task_id)
    check_tenant_scope(actor, task.tenant_id)
    _do_transition(db, task, "cancelled", actor_type="user",
                   actor_id=actor.actor_id, action="task.cancelled",
                   extra={"reason": body.reason})
    db.commit()
    return {"task_id": task.id, "status": task.status}


@app.post("/tasks/{task_id}/requeue")
def requeue_task(task_id: str, body: OwnerActionIn, db: Session = Depends(get_db),
                 actor: Actor = Depends(require_auth)):
    """failed/blocked → queued. Ручное решение владельца."""
    _require_owner(actor)
    task = _get_task(db, task_id)
    check_tenant_scope(actor, task.tenant_id)
    _do_transition(db, task, "queued", actor_type="user",
                   actor_id=actor.actor_id, action="task.requeued",
                   extra={"reason": body.reason})
    db.commit()
    return {"task_id": task.id, "status": task.status}


# --- Approvals ---------------------------------------------------------------

class ApprovalIn(BaseModel):
    tenant_id: str
    task_id: str | None = None
    type: str
    payload: dict = {}
    ttl_hours: float | None = None


class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")


@app.post("/approvals", status_code=201)
def create_approval(body: ApprovalIn, db: Session = Depends(get_db),
                    actor: Actor = Depends(require_auth)):
    require_role(actor, "orchestrator", "admin")
    if not db.get(Tenant, body.tenant_id):
        raise HTTPException(404, "tenant не найден")
    check_tenant_scope(actor, body.tenant_id)
    if body.task_id:
        task = _get_task(db, body.task_id)
        if task.tenant_id != body.tenant_id:
            raise HTTPException(422, "task принадлежит другому tenant")
    ttl = body.ttl_hours if body.ttl_hours is not None else APPROVAL_TTL_HOURS
    a = Approval(**body.model_dump(exclude={"ttl_hours"}),
                 expires_at=utcnow() + timedelta(hours=ttl))
    db.add(a)
    db.flush()
    audit(db, tenant_id=body.tenant_id, actor_type="orchestrator",
          actor_id=actor.actor_id,
          action="approval.requested", entity_type="approval", entity_id=a.id,
          payload={"type": a.type, "task_id": a.task_id,
                   "expires_at": a.expires_at.isoformat()})
    db.commit()
    # Telegram-мост (п.3): публикуем запрос в реестр бота; доставка —
    # зона cron-полла бота. Сбой моста не отменяет approval, но виден явно.
    telegram_notified = None
    if APPROVAL_REGISTRY_PATH:
        try:
            bridge.notify_approval(APPROVAL_REGISTRY_PATH, a,
                                   db.get(Task, a.task_id) if a.task_id else None)
            telegram_notified = True
        except OSError as e:
            telegram_notified = f"ошибка моста: {e}"
    return {"approval_id": a.id, "status": a.status,
            "expires_at": a.expires_at.isoformat(),
            "telegram_notified": telegram_notified}


@app.post("/approvals/{approval_id}/decide")
def decide_approval(approval_id: str, body: DecisionIn, db: Session = Depends(get_db),
                    actor: Actor = Depends(require_auth)):
    """Решение — только токеном владельца (R-01), один раз, до expiry (N-04).
    decided_by = actor из токена, из тела не принимается.

    Атомарный conditional update: UPDATE ... WHERE id AND status='pending'
    AND (expires_at IS NULL OR expires_at > now). rowcount=0 → 409.
    """
    _require_owner(actor)
    a = db.get(Approval, approval_id)
    if not a:
        raise HTTPException(404, "approval не найден")
    check_tenant_scope(actor, a.tenant_id)

    now = utcnow()
    stmt = (
        update(Approval)
        .where(Approval.id == approval_id, Approval.status == "pending")
        .where((Approval.expires_at.is_(None)) | (Approval.expires_at > now))
        .values(status=body.decision, decided_by=actor.actor_id, decided_at=now)
    )
    result = db.execute(stmt, execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        db.rollback()
        current = db.get(Approval, approval_id)
        if current.status != "pending":
            raise HTTPException(409, f"approval уже {current.status}")
        if current.expires_at and aware(current.expires_at) <= now:
            raise HTTPException(409, "approval просрочен")
        raise HTTPException(409, "approval недоступен для решения")

    audit(db, tenant_id=a.tenant_id, actor_type="user", actor_id=actor.actor_id,
          action=f"approval.{body.decision}", entity_type="approval",
          entity_id=a.id, payload={"type": a.type, "task_id": a.task_id})
    db.commit()
    return {"approval_id": a.id, "status": body.decision}


# --- Bridge sync (Telegram-решения → approvals) -------------------------------

@app.post("/bridge/sync")
def bridge_sync(db: Session = Depends(get_db),
                actor: Actor = Depends(require_auth)):
    """Забирает решения владельца из реестра approval-бота (п.3).
    Идемпотентно; применяются только решения decided_by ∈ OWNER_IDS."""
    require_role(actor, "orchestrator", "admin")
    if not APPROVAL_REGISTRY_PATH:
        raise HTTPException(409, "APPROVAL_REGISTRY_PATH не задан — мост выключен")
    applied = bridge.sync_decisions(db, APPROVAL_REGISTRY_PATH, OWNER_IDS)
    return {"applied": applied, "count": len(applied)}


# --- Audit -------------------------------------------------------------------

@app.get("/audit/verify")
def audit_verify(tenant_id: str = Query(...), db: Session = Depends(get_db),
                 actor: Actor = Depends(require_auth)):
    check_tenant_scope(actor, tenant_id)
    ok = verify_chain(db, tenant_id)
    return {"tenant_id": tenant_id, "chain_valid": ok}
