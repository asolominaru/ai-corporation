# Orchestrator — детерминированное ядро Founder AI OS (P0.2)

Статусная машина задач, очередь, аудит. LLM здесь решений не принимает
(docs/TASK_PROTOCOL.md §4): семантику делают агенты, переходы — этот сервис.

Версия 0.2.1 — после повторной проверки 2026-11-06 (R-01/R-02):
- **Аутентификация service-токенами** (`ORCHESTRATOR_TOKENS`, JSON в env):
  личность и роль — из токена, не из тела запроса. Без токена — 401 даже
  с «правильным» owner id. Роли: admin / orchestrator / agent / ci / owner.
- **CI-аттестация** — только токеном роли ci (POST /tasks/{id}/ci), привязана
  к версии артефакта; `/complete` читает аттестацию из БД, а не из тела.
- **Версия результата обязательна:** report без artifact_sha256 → 422;
  approval действует только на версию с тем hash; новая версия после rework
  требует нового approval (R-02).

Версия 0.2.0 — доработка после независимой проверки 2026-11-05
(`review-2026-11-05/`, дефекты N-01..N-05 закрыты, сценарии воспроизведения
превращены в регрессионные тесты, ожидающие безопасного отказа).

## Запуск (dev, SQLite)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ORCHESTRATOR_OWNER_IDS="owner-user-id"
export ORCHESTRATOR_TOKENS='{"tok-owner":{"actor":"owner-user-id","role":"owner"},
  "tok-orch":{"actor":"orch","role":"orchestrator"},
  "tok-admin":{"actor":"admin","role":"admin"},
  "tok-ci":{"actor":"ci-bot","role":"ci"},
  "tok-exec":{"actor":"<agent-id>","role":"agent","tenant_id":"<tenant>"}}'
.venv/bin/uvicorn app.main:app --reload --port 8100
```

Prod: PostgreSQL 16, `ORCHESTRATOR_DATABASE_URL=postgresql+psycopg://...`,
миграции Alembic (TODO P0), RLS-политики по `app.tenant_id`.

## Тесты

```bash
.venv/bin/python -m pytest tests/ -q   # 30 passed: штатные + регрессии N-01..05, R-01/R-02
```

## Что реализовано

- Создание задач строго по `schemas/task.schema.json` (v2); без `why` и без
  `budget.max_usd` задача не создаётся (законы 2 и 7).
- **Нет произвольного /transition.** Только команды: submit / claim / report /
  review / complete / cancel / requeue. Каждая проверяет факты, а не только
  названия статусов (N-01):
  - `complete` требует: был task_run, сдан report; для code_change/deployment —
    `ci_passed=True` + `ci_evidence`; для `requires_human_approval` —
    действующий (не просроченный) approved Approval того типа, решённый
    owner'ом из allowlist, и привязанный к sha256 ТЕКУЩЕЙ версии артефакта.
  - `review` принимает verdict только от назначенного reviewer'а;
    approve невозможен при findings blocker/major; rework ≤ 2 циклов,
    дальше — blocked + эскалация (TASK_PROTOCOL §3).
- Tenant-изоляция на уровне API (N-02): project, reviewer, claim-агент и
  approval обязаны принадлежать tenant'у задачи.
- Бюджет (N-03): суммируется по ВСЕМ попыткам задачи; превышение → blocked;
  claim при исчерпанном бюджете отклоняется; отрицательные/нечисловые
  cost/tokens отклоняются (422). Резервирование до вызова модели —
  зона model-router (TODO P0).
- Approvals (N-04): решение только owner'ом (`ORCHESTRATOR_OWNER_IDS`),
  атомарный conditional update pending → decided (один раз), expiry
  (по умолчанию 48 ч, `APPROVAL_TTL_HOURS`).
- Аудит (N-05): append-only hash-chain по ПОЛНОМУ событию (seq, actor, action,
  entity, payload, created_at) — подмена любого поля ломает цепь;
  `GET /audit/verify` пересчитывает всю цепь. Порядок — монотонный seq
  на tenant.
- Исполнитель ≠ reviewer (закон 3) — и на сдаче отчёта, и на ревью.

## Сознательные ограничения P0

- Нет сетевой аутентификации запросов: owner идентифицируется значением
  actor_id из запроса, сверяемым с allowlist. Это честный уровень защиты
  для приватной сети (Tailscale) на P0, но НЕ полноценная аутентификация —
  полноценная auth появляется с Control Tower (P2). До этого сервис нельзя
  выставлять наружу.
- Очередь без SKIP LOCKED (SQLite dev); в Postgres — `FOR UPDATE SKIP LOCKED`.
- Ретраи/backoff по `retry_policy` — в worker'е (agent-runner), не здесь.
- Отправка approvals в Telegram-бот — TODO (связка с `approval-bot/`).
- Hash-chain аудита проверяется относительно хранилища; внешний anchor
  (экспорт контрольного hash наружу) — P2.

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | /health | healthcheck (проверяет БД) |
| POST | /tenants, /projects, /agents | dev-bootstrap справочников |
| POST | /tasks | создать задачу (schema v2) |
| GET | /tasks?tenant_id=&status= | список |
| GET | /tasks/{id} | карточка + spent_usd |
| POST | /tasks/{id}/submit | created → queued |
| POST | /tasks/{id}/claim | queued/rework → running |
| POST | /tasks/{id}/report | сдача report.json → review/blocked |
| POST | /tasks/{id}/review | verdict назначенного reviewer'а |
| POST | /tasks/{id}/complete | approved → completed (CI + owner approval) |
| POST | /tasks/{id}/cancel | → cancelled (только owner) |
| POST | /tasks/{id}/requeue | failed/blocked → queued (только owner) |
| POST | /approvals | запрос согласования (TTL 48 ч) |
| POST | /approvals/{id}/decide | решение owner'а, атомарно, один раз |
| GET | /audit/verify?tenant_id= | проверка hash-chain |
