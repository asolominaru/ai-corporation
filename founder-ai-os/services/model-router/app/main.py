"""Model Router API (P0.1 — после проверки R-03/R-04).

- Личность и полномочия — из service token (app/auth.py). Без токена — 401.
- /models — только роль admin; endpoint модели обязан быть в серверном
  ALLOWED_BASE_URLS (R-03).
- /complete — только роль orchestrator; tenant запроса = tenant токена.
  Бюджет: закон 7 (нет бюджета — нет вызова), атомарный резерв на уровнях
  task+day+month (R-04), фактический расход записывается честно, даже если
  превысил оценку (overrun=true, дальнейшие вызовы блокируются).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .auth import Actor, require_auth, require_role
from .config import ALLOWED_BASE_URLS
from .db import Base, engine, get_db
from .models import Model, ModelRun
from . import budget as budget_mod
from .routing import pick_model, estimate_cost_usd, actual_cost_usd, NoRoute, PRIVACY_RANK
from . import providers

RESERVE_SAFETY = 1.5
DEFAULT_MAX_TOKENS = 2000


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Founder AI OS — Model Router", version="0.1.1", lifespan=lifespan)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(func.now()))
    return {"status": "ok", "service": "model-router", "version": "0.1.1"}


# --- Реестр моделей (только admin) --------------------------------------------

class ModelIn(BaseModel):
    provider: str
    model_name: str
    tier: str
    input_price_usd: float = Field(ge=0)
    output_price_usd: float = Field(ge=0)
    context_window: int | None = None
    privacy_class: str = "public"
    endpoint_config: dict = {}
    price_verified_at: str | None = None  # ГГГГ-ММ-ДД; без него цена «непроверенная»
    pricing_url: str | None = None

    @field_validator("privacy_class")
    @classmethod
    def _privacy_known(cls, v):
        if v not in PRIVACY_RANK:
            raise ValueError(f"privacy_class должен быть одним из {list(PRIVACY_RANK)}")
        return v

    @field_validator("endpoint_config")
    @classmethod
    def _endpoint_allowed(cls, v):
        base = (v or {}).get("base_url")
        if base and base.rstrip("/") not in ALLOWED_BASE_URLS:
            raise ValueError(
                f"base_url {base} не входит в серверный allowlist (R-03)")
        return v


@app.post("/models", status_code=201)
def register_model(body: ModelIn, db: Session = Depends(get_db),
                   actor: Actor = Depends(require_auth)):
    require_role(actor, "admin")
    if db.execute(select(Model).where(Model.model_name == body.model_name)).first():
        raise HTTPException(409, "модель уже зарегистрирована")
    m = Model(**body.model_dump())
    db.add(m)
    db.commit()
    return {"id": m.id, "model_name": m.model_name}


@app.get("/models")
def list_models(db: Session = Depends(get_db), actor: Actor = Depends(require_auth)):
    require_role(actor, "admin", "orchestrator")
    return [
        {"id": m.id, "provider": m.provider, "model_name": m.model_name,
         "tier": m.tier, "privacy_class": m.privacy_class, "status": m.status,
         "input_price_usd": float(m.input_price_usd),
         "output_price_usd": float(m.output_price_usd),
         "price_verified_at": m.price_verified_at, "pricing_url": m.pricing_url}
        for m in db.execute(select(Model)).scalars().all()
    ]


# --- Вызов (только orchestrator) ----------------------------------------------

class CompleteIn(BaseModel):
    tenant_id: str
    task_id: str
    task_type: str
    messages: list[dict]
    data_privacy: str = "public"
    task_budget_max_usd: float | None = None  # из задачи orchestrator'а; None = стоп
    avoid_model_id: str | None = None         # для review: не модель автора
    est_tokens_in: int = Field(default=4000, ge=0)
    max_tokens_out: int = Field(default=DEFAULT_MAX_TOKENS, ge=1, le=32000)

    @field_validator("data_privacy")
    @classmethod
    def _privacy_known(cls, v):
        if v not in PRIVACY_RANK:
            raise ValueError(f"неизвестный data_privacy: {v}")
        return v


@app.post("/complete")
def complete(body: CompleteIn, db: Session = Depends(get_db),
             actor: Actor = Depends(require_auth)):
    require_role(actor, "orchestrator")
    # tenant запроса обязан совпадать с tenant токена (R-04.1)
    if actor.tenant_id and actor.tenant_id != body.tenant_id:
        raise HTTPException(403, "токен orchestrator привязан к другому tenant")

    # Закон 7: платный вызов без заданного бюджета задачи запрещён.
    if body.task_budget_max_usd is None or body.task_budget_max_usd <= 0:
        raise HTTPException(402, "budget задачи не задан — платный вызов заблокирован")

    try:
        model = pick_model(db, task_type=body.task_type,
                           data_privacy=body.data_privacy,
                           avoid_model_id=body.avoid_model_id)
    except NoRoute as e:
        raise HTTPException(409, str(e)) from e

    estimate = estimate_cost_usd(model, body.est_tokens_in, body.max_tokens_out) * RESERVE_SAFETY

    # Атомарный резерв task+day+month (R-04).
    try:
        reservation = budget_mod.reserve(
            db, tenant_id=body.tenant_id, task_id=body.task_id,
            task_cap_usd=body.task_budget_max_usd, amount_usd=estimate)
        db.commit()
    except budget_mod.BudgetExceeded as e:
        db.rollback()
        raise HTTPException(402, str(e)) from e

    try:
        result = providers.chat(model, body.messages, body.max_tokens_out)
    except providers.ProviderError as e:
        budget_mod.release(db, reservation)
        _record_run(db, body, model, 0, 0, 0, False, str(e))
        db.commit()
        status = 503 if isinstance(e, providers.ProviderNotConfigured) else 502
        raise HTTPException(status, str(e)) from e

    actual = actual_cost_usd(model, result.tokens_in, result.tokens_out)
    budget_mod.commit(db, reservation, actual)  # честно, даже если > estimate (R-04)
    run = _record_run(db, body, model, result.tokens_in, result.tokens_out,
                      actual, True, None, latency_ms=result.latency_ms)
    db.commit()

    task_budget = db.execute(
        select(budget_mod.TaskBudget).where(
            budget_mod.TaskBudget.tenant_id == body.tenant_id,
            budget_mod.TaskBudget.task_id == body.task_id)
    ).scalars().first()
    task_spent = float(task_budget.spent_usd) if task_budget else actual

    return {
        "run_id": run.id,
        "model": model.model_name,
        "text": result.text,
        "usage": {"tokens_in": result.tokens_in, "tokens_out": result.tokens_out,
                  "cost_usd": actual, "latency_ms": result.latency_ms},
        "task_spent_usd": task_spent,
        "overrun": actual > estimate,  # факт превысил резерв — учтено честно
    }


def _record_run(db, body, model, tokens_in, tokens_out, cost, success, error,
                latency_ms=None):
    run = ModelRun(
        tenant_id=body.tenant_id, task_id=body.task_id, task_type=body.task_type,
        model_id=model.id, tokens_in=tokens_in, tokens_out=tokens_out,
        cost_usd=cost, success=success, error=error, latency_ms=latency_ms,
    )
    db.add(run)
    db.flush()
    return run


# --- Отчётность ---------------------------------------------------------------

@app.get("/budget/{tenant_id}")
def budget_status(tenant_id: str, db: Session = Depends(get_db),
                  actor: Actor = Depends(require_auth)):
    require_role(actor, "admin", "orchestrator")
    if actor.tenant_id and actor.tenant_id != tenant_id:
        raise HTTPException(403, "токен привязан к другому tenant")
    return budget_mod.status(db, tenant_id)


@app.get("/usage")
def usage(tenant_id: str, task_id: str | None = None, db: Session = Depends(get_db),
          actor: Actor = Depends(require_auth)):
    require_role(actor, "admin", "orchestrator")
    if actor.tenant_id and actor.tenant_id != tenant_id:
        raise HTTPException(403, "токен привязан к другому tenant")
    q = select(ModelRun).where(ModelRun.tenant_id == tenant_id)
    if task_id:
        q = q.where(ModelRun.task_id == task_id)
    rows = db.execute(q.order_by(ModelRun.created_at.desc()).limit(200)).scalars().all()
    return [
        {"run_id": r.id, "task_id": r.task_id, "task_type": r.task_type,
         "tokens_in": r.tokens_in, "tokens_out": r.tokens_out,
         "cost_usd": float(r.cost_usd), "success": r.success, "error": r.error,
         "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]
