"""Append-only аудит с hash-chain по полному событию (docs/DATABASE.md, N-05).

hash = sha256(prev_hash || canonical(event)), где event включает seq,
actor_type, actor_id, action, entity_type, entity_id, payload, created_at.
Подмена ЛЮБОГО поля прошлой записи ломает цепь — verify_chain это ловит.
Первая запись цепи tenant'а использует GENESIS как prev_hash.

Ограничение: целостность проверяется относительно хранилища; внешний
контрольный экспорт (anchor наружу) — отдельная задача P2.
"""
import hashlib
import json

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .models import AuditLog, utcnow, aware

GENESIS = "0" * 64


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      default=str)


def _event_dict(entry_fields: dict) -> str:
    return _canonical(entry_fields)


def _ts(dt) -> str | None:
    """Единая сериализация времени: всегда aware-UTC isoformat (SQLite
    возвращает naive — нормализуем, иначе hash на записи и проверке разойдётся)."""
    a = aware(dt)
    return a.isoformat() if a else None


def _next_seq(db: Session, tenant_id: str) -> int:
    current = db.execute(
        select(func.max(AuditLog.seq)).where(AuditLog.tenant_id == tenant_id)
    ).scalar()
    return (current or 0) + 1


def audit(
    db: Session,
    *,
    tenant_id: str,
    actor_type: str,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict | None = None,
) -> AuditLog:
    payload = payload or {}
    prev_row = db.execute(
        select(AuditLog.seq, AuditLog.hash)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.seq.desc())
        .limit(1)
    ).first()
    prev_hash, seq = (prev_row[1], prev_row[0] + 1) if prev_row else (GENESIS, 1)

    created = utcnow()
    event = {
        "seq": seq,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
        "created_at": _ts(created),
    }
    h = hashlib.sha256((prev_hash + _event_dict(event)).encode("utf-8")).hexdigest()
    entry = AuditLog(
        tenant_id=tenant_id, seq=seq,
        actor_type=actor_type, actor_id=actor_id, action=action,
        entity_type=entity_type, entity_id=entity_id, payload=payload,
        prev_hash=prev_hash, hash=h, created_at=created,
    )
    db.add(entry)
    return entry


def verify_chain(db: Session, tenant_id: str) -> bool:
    """Проверка целостности цепи tenant'а. True — цепь не нарушена.

    Пересчитывает hash каждой записи из ВСЕХ её полей; подмена actor/action/
    payload/времени/порядка обнаруживается.
    """
    rows = db.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.seq)
    ).scalars().all()
    prev = GENESIS
    for expected_seq, row in enumerate(rows, start=1):
        if row.seq != expected_seq or row.prev_hash != prev:
            return False
        event = {
            "seq": row.seq,
            "actor_type": row.actor_type,
            "actor_id": row.actor_id,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "payload": row.payload,
            "created_at": _ts(row.created_at),
        }
        if row.hash != hashlib.sha256((prev + _event_dict(event)).encode()).hexdigest():
            return False
        prev = row.hash
    return True
