"""Модели model-router: реестр LLM, вызовы, бюджетный ledger.

budget_ledger — одна строка на (tenant, период): атомарное резервирование
через conditional UPDATE (WHERE spent+reserved+X <= cap), что закрывает
гонку параллельных задач (K-12).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, JSON, Boolean, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Model(Base):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100), unique=True)
    tier: Mapped[str] = mapped_column(String(30))  # flagship_reasoning|coding_worker|long_context|mid|cheap
    input_price_usd: Mapped[float] = mapped_column(Numeric(14, 8))   # за 1M токенов
    output_price_usd: Mapped[float] = mapped_column(Numeric(14, 8))
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # public < anonymized < personal_data < confidential
    privacy_class: Mapped[str] = mapped_column(String(20), default="public")
    status: Mapped[str] = mapped_column(String(20), default="active")
    endpoint_config: Mapped[dict] = mapped_column(JSON, default=dict)
    price_verified_at: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ГГГГ-ММ-ДД
    pricing_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ModelRun(Base):
    """Каждый вызов LLM. Пишется только router'ом. Append-only."""
    __tablename__ = "model_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    task_type: Mapped[str] = mapped_column(String(50))
    model_id: Mapped[str] = mapped_column(String(36))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(14, 8), default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BudgetLedger(Base):
    """Агрегированный бюджет tenant'а за период (day=YYYY-MM-DD / month=YYYY-MM)."""
    __tablename__ = "budget_ledger"
    __table_args__ = (UniqueConstraint("tenant_id", "period_kind", "period"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    period_kind: Mapped[str] = mapped_column(String(10))  # day|month
    period: Mapped[str] = mapped_column(String(10))
    reserved_usd: Mapped[float] = mapped_column(Numeric(14, 8), default=0)
    spent_usd: Mapped[float] = mapped_column(Numeric(14, 8), default=0)
    cap_usd: Mapped[float] = mapped_column(Numeric(14, 2))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Reservation(Base):
    """Активное резервирование под конкретный вызов. Закрывается commit'ом
    (фактические траты) или release (ошибка/отказ до вызова).

    day_period/month_period зафиксированы в момент резерва: settlement идёт
    именно в них, даже если вызов завершился после полуночи (R-04)."""
    __tablename__ = "reservations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    amount_usd: Mapped[float] = mapped_column(Numeric(14, 8))
    day_period: Mapped[str] = mapped_column(String(10))
    month_period: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10), default="open")  # open|committed|released
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaskBudget(Base):
    """Бюджет конкретной задачи: атомарный резерв на уровне задачи (R-04).
    Перекрывающиеся вызовы одной задачи не обходят её лимит."""
    __tablename__ = "task_budgets"
    __table_args__ = (UniqueConstraint("tenant_id", "task_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    cap_usd: Mapped[float] = mapped_column(Numeric(14, 2))
    reserved_usd: Mapped[float] = mapped_column(Numeric(14, 8), default=0)
    spent_usd: Mapped[float] = mapped_column(Numeric(14, 8), default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow)
