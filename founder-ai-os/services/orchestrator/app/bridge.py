"""Мост orchestrator ↔ approval-бот (п.3 повторной проверки).

Транспорт — requests.json бота. Telegram остаётся зоной бота:
- orchestrator ПИШЕТ pending-запросы (source="orchestrator", message_id=null);
- cron-полл бота отправляет их владельцу и записывает решения;
- orchestrator ЗАБИРАЕТ решения через sync_decisions().

Гонки чтение–изменение–запись между процессами закрыты fcntl.flock
на <registry>.lock — тот же протокол реализован в approval-bot/approvals.py.

Решение применяется тем же атомарным conditional UPDATE, что и
POST /approvals/{id}/decide: повторная синхронизация — no-op.
"""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from .audit import audit
from .models import Approval, Task, utcnow, aware

# Метки кнопок → решение orchestrator'а. Неизвестная метка решения
# не применяется (fail closed) и остаётся видимой в реестре бота.
DECISION_MAP = {"Согласовать": "approved", "Отклонить": "rejected"}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lock_path(registry_path: str) -> str:
    return registry_path + ".lock"


@contextmanager
def locked_registry(registry_path: str):
    """Атомарное read-modify-write реестра под эксклюзивной блокировкой."""
    with open(_lock_path(registry_path), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.exists(registry_path):
            with open(registry_path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        yield data
        tmp = registry_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, registry_path)


def notify_approval(registry_path: str, approval: Approval, task: Task | None) -> None:
    """Публикует pending-запрос в реестр бота. Бот доставит его владельцу
    при ближайшем poll. Идемпотентно: request_id = approval.id."""
    artifact = (approval.payload or {}).get("artifact_sha256")
    lines = [
        f"Тип: {approval.type}",
        f"Approval: {approval.id}",
    ]
    if task is not None:
        lines.append(f"Задача: {task.goal[:120]}")
        lines.append(f"Task: {task.id}")
    if artifact:
        lines.append(f"Версия артефакта (sha256): {artifact}")
    if approval.expires_at:
        lines.append(f"Действует до: {aware(approval.expires_at).isoformat()}")
    entry = {
        "request_id": approval.id,
        "source": "orchestrator",
        "title": f"{approval.type}: {(task.goal[:60] if task else approval.type)}",
        "body": "\n".join(lines),
        "options": list(DECISION_MAP),
        "decision_map": DECISION_MAP,
        "artifact_sha256": artifact,
        "status": "pending",
        "created_at": _utcnow_iso(),
        "expires_at": (aware(approval.expires_at).isoformat()
                       if approval.expires_at else None),
        "message_chat_id": None,
        "message_id": None,
        "decision": None, "decided_by": None, "decided_at": None,
    }
    with locked_registry(registry_path) as registry:
        existing = registry.get(approval.id)
        if existing and existing.get("status") != "pending":
            return  # решение уже есть — не сбрасываем
        registry[approval.id] = entry


def sync_decisions(db: Session, registry_path: str, owner_ids) -> list[dict]:
    """Переносит решения владельца из реестра бота в approvals.

    Применяет только записи source="orchestrator" со статусом decided/expired.
    Решение принимается, только если decided_by ∈ owner_ids (та же проверка,
    что и у API-решения). Возвращает список применённых изменений.
    """
    if not os.path.exists(registry_path):
        return []
    with open(_lock_path(registry_path), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        with open(registry_path, encoding="utf-8") as f:
            registry = json.load(f)

    applied = []
    now = utcnow()
    for rid, req in registry.items():
        if req.get("source") != "orchestrator":
            continue
        if req.get("status") not in ("decided", "expired"):
            continue
        approval = db.get(Approval, rid)
        if approval is None or approval.status != "pending":
            continue  # уже решён (API или прошлым sync) — идемпотентность

        if req["status"] == "expired":
            target, decided_by, decided_at = "expired", None, now
        else:
            decision_map = req.get("decision_map") or DECISION_MAP
            target = decision_map.get(req.get("decision"))
            if target not in ("approved", "rejected"):
                continue  # неизвестная метка — не применяем, видимо в реестре
            decided_by = str(req.get("decided_by") or "")
            if decided_by not in owner_ids:
                audit(db, tenant_id=approval.tenant_id, actor_type="orchestrator",
                      actor_id="telegram-bridge", action="approval.sync_rejected",
                      entity_type="approval", entity_id=approval.id,
                      payload={"reason": "decided_by не входит в OWNER_IDS",
                               "decided_by": decided_by})
                continue
            raw_at = req.get("decided_at")
            try:
                decided_at = datetime.fromisoformat(raw_at) if raw_at else now
            except ValueError:
                decided_at = now
            if approval.expires_at and aware(approval.expires_at) <= decided_at:
                target = "expired"  # решение пришло после дедлайна

        stmt = (
            update(Approval)
            .where(Approval.id == approval.id, Approval.status == "pending")
            .values(status=target, decided_by=decided_by, decided_at=decided_at)
        )
        result = db.execute(stmt, execution_options={"synchronize_session": False})
        if result.rowcount != 1:
            db.rollback()
            continue
        audit(db, tenant_id=approval.tenant_id, actor_type="user",
              actor_id=decided_by or "telegram-bridge",
              action=f"approval.{target}", entity_type="approval",
              entity_id=approval.id,
              payload={"type": approval.type, "task_id": approval.task_id,
                       "channel": "telegram", "request_id": rid})
        applied.append({"approval_id": approval.id, "status": target,
                        "decided_by": decided_by})
    db.commit()
    return applied
