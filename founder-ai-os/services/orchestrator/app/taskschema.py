"""Валидация задач по канонической JSON Schema (schemas/task.schema.json, v2).

Закон 2: задачи — только по схеме. Закон 7: budget.max_usd обязателен,
null-бюджет блокирует платные вызовы.
"""
import json
import uuid
from functools import lru_cache

import jsonschema

from .config import TASK_SCHEMA_PATH


@lru_cache(maxsize=1)
def load_task_schema() -> dict:
    with open(TASK_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


class TaskValidationError(ValueError):
    pass


def validate_task_payload(payload: dict) -> dict:
    """Валидирует payload новой задачи. task_id/status присваивает orchestrator:
    подставляем валидные заглушки, чтобы прогнать schema-валидацию остального."""
    candidate = dict(payload)
    candidate.setdefault("task_id", str(uuid.uuid4()))
    candidate.setdefault("status", "created")
    try:
        jsonschema.validate(candidate, load_task_schema())
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.absolute_path) or "(root)"
        raise TaskValidationError(f"task payload невалиден: {path}: {e.message}") from e

    budget = candidate.get("budget") or {}
    if not budget.get("max_usd"):
        raise TaskValidationError("budget.max_usd обязателен: null-бюджет = стоп (закон 7)")
    return candidate
