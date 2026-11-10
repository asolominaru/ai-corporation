"""Маршрутизация: task_type → tier → активная модель с допустимым privacy.

Правило privacy: данные класса X можно отправлять только в модель,
допущенную к X или выше (public < anonymized < personal_data < confidential).
Code review другой моделью, чем автор, обеспечивает orchestrator (закон 3);
router дополнительно исключает avoid_model_id.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Model

PRIVACY_RANK = {"public": 0, "anonymized": 1, "personal_data": 2, "confidential": 3}

TASK_TYPE_TIER = {
    "strategy_architecture": "flagship_reasoning",
    "coding_backend": "coding_worker",
    "coding_frontend": "coding_worker",
    "code_review": "coding_worker",
    "independent_audit": "long_context",
    "writing_ux": "mid",
    "classification_qualification": "cheap",
    "rnd_research": "flagship_reasoning",
}


class NoRoute(Exception):
    pass


def estimate_cost_usd(model: Model, est_tokens_in: int, est_tokens_out: int) -> float:
    return (est_tokens_in * float(model.input_price_usd)
            + est_tokens_out * float(model.output_price_usd)) / 1_000_000


def actual_cost_usd(model: Model, tokens_in: int, tokens_out: int) -> float:
    return estimate_cost_usd(model, tokens_in, tokens_out)


def pick_model(db: Session, *, task_type: str, data_privacy: str = "public",
               avoid_model_id: str | None = None) -> Model:
    tier = TASK_TYPE_TIER.get(task_type, "mid")
    need = PRIVACY_RANK.get(data_privacy)
    if need is None:
        raise NoRoute(f"неизвестный privacy-класс данных: {data_privacy}")
    candidates = db.execute(
        select(Model).where(Model.tier == tier, Model.status == "active")
    ).scalars().all()
    allowed = [m for m in candidates
               if PRIVACY_RANK.get(m.privacy_class, -1) >= need
               and m.id != avoid_model_id]
    if not allowed:
        raise NoRoute(f"нет активной модели tier={tier} для privacy={data_privacy}")
    # Дешевлее — раньше; арена качества заменит эту эвристику на P5.
    return min(allowed, key=lambda m: float(m.input_price_usd) + float(m.output_price_usd))
