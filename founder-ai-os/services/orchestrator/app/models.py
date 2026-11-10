"""Модели ядра. Зеркалят docs/DATABASE.md §«Таблицы».

Dev-хранилище — SQLite, поэтому uuid храним как String(36), JSON — как
sqlalchemy.JSON. В prod (PostgreSQL) та же схема создаётся Alembic-миграциями
с нативными uuid/jsonb и RLS-политиками.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Numeric, DateTime, ForeignKey, JSON, Boolean, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    """SQLite возвращает naive datetime; считаем его UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    plan: Mapped[str] = mapped_column(String(50), default="founder")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    department_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active")
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    role_code: Mapped[str] = mapped_column(String(100))  # из blueprints/agents/*.yaml
    name: Mapped[str] = mapped_column(String(200))
    tools: Mapped[list] = mapped_column(JSON, default=list)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    model_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    budget_monthly_usd: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    reviewer_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")


class ModelRegistry(Base):
    """Реестр LLM (таблица `models` в DATABASE.md; имя класса во избежание коллизии)."""
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    input_price_usd: Mapped[float] = mapped_column(Numeric(12, 6))
    output_price_usd: Mapped[float] = mapped_column(Numeric(12, 6))
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    privacy_class: Mapped[str] = mapped_column(String(20), default="public")
    status: Mapped[str] = mapped_column(String(20), default="active")
    endpoint_config: Mapped[dict] = mapped_column(JSON, default=dict)


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # = task_id из схемы
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))
    department: Mapped[str] = mapped_column(String(30))
    workflow_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    parent_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    goal: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text)
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_output: Mapped[dict] = mapped_column(JSON)
    acceptance_criteria: Mapped[list] = mapped_column(JSON)
    tools_allowed: Mapped[list] = mapped_column(JSON, default=list)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String(10), default="REVIEW")
    primary_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fallback_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    budget: Mapped[dict] = mapped_column(JSON)  # {max_usd, max_tokens}; null-бюджет = стоп (закон 7)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer: Mapped[str] = mapped_column(String(36))
    retry_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    escalation_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    requires_human_approval: Mapped[list] = mapped_column(JSON, default=list)
    next_action: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="created", index=True)
    created_by: Mapped[str] = mapped_column(String(100), default="api")
    # sha256 текущей версии артефакта результата; approval и complete
    # обязаны ссылаться именно на неё (закон 4).
    artifact_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rework_count: Mapped[int] = mapped_column(Integer, default=0)
    # Аттестация CI: ставится только ролью ci через POST /tasks/{id}/ci (R-01).
    ci_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ci_evidence: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ci_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaskRun(Base):
    """Одна попытка исполнения задачи агентом."""
    __tablename__ = "task_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"))
    mode: Mapped[str] = mapped_column(String(10), default="SOLO")
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|done|failed
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    worktree_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(200), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(50))  # payment|deploy|contract|...
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected|expired
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    channel_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class AuditLog(Base):
    """Append-only журнал с hash-chain по ПОЛНОМУ событию (N-05).

    hash = sha256(prev_hash || canonical({seq, actor_type, actor_id, action,
    entity_type, entity_id, payload, created_at})). Изменение любого поля
    прошлой записи ломает цепь и обнаруживается verify_chain.
    seq — монотонный номер записи в цепи tenant'а (стабильный порядок).
    """
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    actor_type: Mapped[str] = mapped_column(String(20))  # agent|user|orchestrator
    actor_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(36))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CostLog(Base):
    """Append-only лог стоимости."""
    __tablename__ = "cost_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    entity_type: Mapped[str] = mapped_column(String(30))  # model_run|task|workflow|...
    entity_id: Mapped[str] = mapped_column(String(36))
    cost_type: Mapped[str] = mapped_column(String(20))  # ai|infra|human_estimate
    amount_usd: Mapped[float] = mapped_column(Numeric(12, 6))
    business_value_usd: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
