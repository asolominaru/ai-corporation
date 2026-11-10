"""Атомарный бюджетный guard (K-12, R-04).

Три уровня лимитов, ВСЕ резервируются атомарно conditional UPDATE'ами:
1. task (cap задачи), 2. day (тенант/день), 3. month (тенант/месяц).
Отказ любого уровня → rollback всего резерва. Перекрывающиеся вызовы
одной задачи не обходят task cap: второй conditional UPDATE получит
rowcount=0.

Settlement (commit/release) идёт в периоды, ЗАФИКСИРОВАННЫЕ в резерве, —
переход через полночь/границу месяца не теряет траты и не оставляет
зависших резервов. Settlement идемпотентен: повторный commit/release
по закрытому резерву отклоняется.

Уже понесённый расход записывается честно, даже если факт превысил
оценку: spent может превысить cap — тогда все следующие резервы
блокируются до разбора (ledger явно покажет перерасход).
"""
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .config import DAILY_CAP_USD, MONTHLY_CAP_USD
from .models import BudgetLedger, Reservation, TaskBudget, utcnow


class BudgetExceeded(Exception):
    def __init__(self, scope: str, period: str, cap: float):
        super().__init__(f"лимит {scope} {period}: cap ${cap}")
        self.scope, self.period, self.cap = scope, period, cap


def _current_periods():
    now = datetime.now(timezone.utc)
    return (now.strftime("%Y-%m-%d"), now.strftime("%Y-%m"))


def _ensure_ledger(db: Session, tenant_id: str, kind: str, period: str, cap: float):
    row = db.execute(
        select(BudgetLedger).where(
            BudgetLedger.tenant_id == tenant_id,
            BudgetLedger.period_kind == kind,
            BudgetLedger.period == period)
    ).scalars().first()
    if not row:
        row = BudgetLedger(tenant_id=tenant_id, period_kind=kind,
                           period=period, cap_usd=cap)
        db.add(row)
        db.flush()
    return row


def _ensure_task_budget(db: Session, tenant_id: str, task_id: str, cap: float):
    row = db.execute(
        select(TaskBudget).where(TaskBudget.tenant_id == tenant_id,
                                 TaskBudget.task_id == task_id)
    ).scalars().first()
    if not row:
        row = TaskBudget(tenant_id=tenant_id, task_id=task_id, cap_usd=cap)
        db.add(row)
        db.flush()
    return row


def reserve(db: Session, *, tenant_id: str, task_id: str,
            task_cap_usd: float, amount_usd: float) -> Reservation:
    """Атомарно резервирует amount на уровнях task+day+month.
    Бросает BudgetExceeded; при отказе транзакцию откатывает вызывающий."""
    if amount_usd <= 0:
        raise ValueError("резерв должен быть положительным")

    day, month = _current_periods()

    # 1. Уровень задачи.
    _ensure_task_budget(db, tenant_id, task_id, task_cap_usd)
    stmt = (
        update(TaskBudget)
        .where(TaskBudget.tenant_id == tenant_id, TaskBudget.task_id == task_id,
               TaskBudget.spent_usd + TaskBudget.reserved_usd + amount_usd
               <= TaskBudget.cap_usd)
        .values(reserved_usd=TaskBudget.reserved_usd + amount_usd)
    )
    res = db.execute(stmt, execution_options={"synchronize_session": False})
    if res.rowcount != 1:
        raise BudgetExceeded("task", task_id, task_cap_usd)

    # 2–3. День и месяц tenant'а.
    try:
        for kind, period, cap in (("day", day, DAILY_CAP_USD),
                                  ("month", month, MONTHLY_CAP_USD)):
            _ensure_ledger(db, tenant_id, kind, period, cap)
            stmt = (
                update(BudgetLedger)
                .where(BudgetLedger.tenant_id == tenant_id,
                       BudgetLedger.period_kind == kind,
                       BudgetLedger.period == period,
                       BudgetLedger.spent_usd + BudgetLedger.reserved_usd + amount_usd
                       <= BudgetLedger.cap_usd)
                .values(reserved_usd=BudgetLedger.reserved_usd + amount_usd)
            )
            res = db.execute(stmt, execution_options={"synchronize_session": False})
            if res.rowcount != 1:
                raise BudgetExceeded(kind, period, cap)
    except BudgetExceeded:
        # откатываем резерв уровня задачи
        stmt = (
            update(TaskBudget)
            .where(TaskBudget.tenant_id == tenant_id, TaskBudget.task_id == task_id)
            .values(reserved_usd=TaskBudget.reserved_usd - amount_usd)
        )
        db.execute(stmt, execution_options={"synchronize_session": False})
        raise

    r = Reservation(tenant_id=tenant_id, task_id=task_id, amount_usd=amount_usd,
                    day_period=day, month_period=month)
    db.add(r)
    db.flush()
    return r


def _settle_ledgers(db: Session, reservation: Reservation, actual_usd: float | None):
    """Обновляет day/month-строки периодов РЕЗЕРВА (не текущих)."""
    for kind, period in (("day", reservation.day_period),
                         ("month", reservation.month_period)):
        values = {"reserved_usd": BudgetLedger.reserved_usd - reservation.amount_usd}
        if actual_usd is not None:
            values["spent_usd"] = BudgetLedger.spent_usd + actual_usd
        stmt = (
            update(BudgetLedger)
            .where(BudgetLedger.tenant_id == reservation.tenant_id,
                   BudgetLedger.period_kind == kind,
                   BudgetLedger.period == period)
            .values(**values)
        )
        db.execute(stmt, execution_options={"synchronize_session": False})


def _settle_task(db: Session, reservation: Reservation, actual_usd: float | None):
    values = {"reserved_usd": TaskBudget.reserved_usd - reservation.amount_usd}
    if actual_usd is not None:
        values["spent_usd"] = TaskBudget.spent_usd + actual_usd
    stmt = (
        update(TaskBudget)
        .where(TaskBudget.tenant_id == reservation.tenant_id,
               TaskBudget.task_id == reservation.task_id)
        .values(**values)
    )
    db.execute(stmt, execution_options={"synchronize_session": False})


def _close_reservation(db: Session, reservation: Reservation, new_status: str) -> bool:
    """Атомарно закрывает резерв: UPDATE ... WHERE id AND status='open'.
    True — закрыт нами; False — уже закрыт (идемпотентность/гонка)."""
    stmt = (
        update(Reservation)
        .where(Reservation.id == reservation.id, Reservation.status == "open")
        .values(status=new_status, closed_at=utcnow())
    )
    res = db.execute(stmt, execution_options={"synchronize_session": False})
    if res.rowcount == 1:
        reservation.status = new_status
        return True
    db.refresh(reservation)
    return False


def commit(db: Session, reservation: Reservation, actual_usd: float):
    """Фиксирует фактический расход. Идемпотентно: повторный commit отклонён."""
    if not _close_reservation(db, reservation, "committed"):
        raise ValueError("резерв уже закрыт")
    _settle_ledgers(db, reservation, actual_usd)
    _settle_task(db, reservation, actual_usd)


def release(db: Session, reservation: Reservation):
    """Возвращает резерв без списания (вызов не состоялся). Идемпотентно."""
    if not _close_reservation(db, reservation, "released"):
        return
    _settle_ledgers(db, reservation, None)
    _settle_task(db, reservation, None)


def status(db: Session, tenant_id: str) -> dict:
    day, month = _current_periods()
    out = {}
    for kind, period, cap in (("day", day, DAILY_CAP_USD),
                              ("month", month, MONTHLY_CAP_USD)):
        row = db.execute(
            select(BudgetLedger).where(
                BudgetLedger.tenant_id == tenant_id,
                BudgetLedger.period_kind == kind,
                BudgetLedger.period == period)
        ).scalars().first()
        out[kind] = {
            "period": period,
            "cap_usd": float(row.cap_usd) if row else cap,
            "spent_usd": float(row.spent_usd) if row else 0.0,
            "reserved_usd": float(row.reserved_usd) if row else 0.0,
            "overrun": bool(row and float(row.spent_usd) > float(row.cap_usd)),
        }
    return out
