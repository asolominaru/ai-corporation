"""Статусная машина задач — docs/TASK_PROTOCOL.md §2.

Переходы выполняет ТОЛЬКО orchestrator. Агент возвращает report.json,
решение о переходе — здесь. Все переходы пишутся в audit_logs.

created → queued → running → review → approved → completed
                   ↑          ↓
                   └── rework ┘
running → blocked → queued
running → failed (retry исчерпаны)
любой → cancelled (только человек)
"""
from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    REVIEW = "review"
    REWORK = "rework"
    APPROVED = "approved"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Допустимые переходы: from -> {to: кто может инициировать}
# actor: "orchestrator" — система/агентский поток, "human" — только человек.
TRANSITIONS: dict[TaskStatus, dict[TaskStatus, str]] = {
    TaskStatus.CREATED: {
        TaskStatus.QUEUED: "orchestrator",
        TaskStatus.CANCELLED: "human",
    },
    TaskStatus.QUEUED: {
        TaskStatus.RUNNING: "orchestrator",   # claim агентом
        TaskStatus.CANCELLED: "human",
    },
    TaskStatus.RUNNING: {
        TaskStatus.REVIEW: "orchestrator",    # report.json сдан
        TaskStatus.BLOCKED: "orchestrator",   # в т.ч. превышение бюджета
        TaskStatus.FAILED: "orchestrator",    # retry исчерпаны
        TaskStatus.CANCELLED: "human",
    },
    TaskStatus.BLOCKED: {
        TaskStatus.QUEUED: "orchestrator",    # разблокировано
        TaskStatus.CANCELLED: "human",
    },
    TaskStatus.REVIEW: {
        TaskStatus.APPROVED: "orchestrator",  # reviewer verdict=approve
        TaskStatus.REWORK: "orchestrator",    # request_changes (≤2 циклов)
        TaskStatus.CANCELLED: "human",
    },
    TaskStatus.REWORK: {
        TaskStatus.RUNNING: "orchestrator",   # findings вернулись автору
        TaskStatus.CANCELLED: "human",
    },
    TaskStatus.APPROVED: {
        TaskStatus.COMPLETED: "orchestrator", # +зелёный CI для code_change
        TaskStatus.CANCELLED: "human",
    },
    TaskStatus.FAILED: {
        TaskStatus.QUEUED: "human",           # ручной requeue
        TaskStatus.CANCELLED: "human",
    },
    TaskStatus.COMPLETED: {},
    TaskStatus.CANCELLED: {},
}

CODE_OUTPUT_TYPES = {"code_change", "deployment"}


class TransitionError(ValueError):
    pass


def check_transition(
    current: str,
    target: str,
    *,
    actor_type: str,
    expected_output_type: str | None = None,
    ci_passed: bool | None = None,
) -> TaskStatus:
    """Валидирует переход. Возвращает целевой статус или бросает TransitionError.

    Инварианты:
    - completed достижим только из approved;
    - для code_change/deployment completed требует ci_passed=True;
    - cancelled — только человек (вшито в TRANSITIONS).
    """
    try:
        cur, tgt = TaskStatus(current), TaskStatus(target)
    except ValueError as e:
        raise TransitionError(f"неизвестный статус: {e}") from e

    allowed = TRANSITIONS.get(cur, {})
    if tgt not in allowed:
        raise TransitionError(f"переход {cur.value} → {tgt.value} запрещён")

    required_actor = allowed[tgt]
    if required_actor == "human" and actor_type != "user":
        raise TransitionError(f"переход {cur.value} → {tgt.value} доступен только человеку")

    if tgt == TaskStatus.COMPLETED:
        if cur != TaskStatus.APPROVED:
            raise TransitionError("completed возможен только из approved")
        if expected_output_type in CODE_OUTPUT_TYPES and ci_passed is not True:
            raise TransitionError("completed для кода требует зелёного CI (ci_passed=True)")

    return tgt
