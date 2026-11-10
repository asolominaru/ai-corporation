# TASK_PROTOCOL.md

## 1. Task Protocol

Все задачи в системе — записи по единой JSON Schema: [schemas/task.schema.json](../schemas/task.schema.json). Ключевые поля:

| Поле | Назначение |
|---|---|
| `task_id` | uuid, присваивает orchestrator |
| `tenant_id`, `project_id`, `department` | принадлежность и изоляция |
| `goal`, `why` | что и зачем; `why` обязателен — задача без бизнес-причины не создаётся |
| `input`, `context` | входные данные и ссылки на knowledge |
| `expected_output` | описание законченного продукта — что физически должно существовать после выполнения |
| `acceptance_criteria` | массив машинно-проверяемых критериев: `{type: test|command|http_check|file_exists|metric, ...}`. Критерий «выглядит хорошо» недопустим |
| `tools_allowed`, `permissions` | whitelist инструментов и прав на этот запуск (пересечение с правами агента) |
| `primary_model`, `fallback_model` | подсказка router'у; окончательный выбор — за router |
| `budget` | лимит USD на задачу; превышение → `blocked` |
| `deadline` | для SLA и эскалаций |
| `reviewer` | кто проверяет (обязателен, не автор) |
| `retry_policy` | `max_attempts`, `backoff` |
| `escalation_policy` | кому и когда эскалировать |
| `next_action` | что запускается после `completed` (workflow chaining) |

## 2. Статусная машина

```
created → queued → running → review → approved → completed
                    ↑          ↓
                    └── rework ┘
running → blocked → queued (после разблокировки)
running → failed (исчерпаны retry)
любой → cancelled (только человек)
```

Переходы выполняет только orchestrator. Агент не ставит себе статус — он возвращает `report.json`, а orchestrator решает переход. Переходы пишутся в `audit_logs`.

Инвариант: задача не может стать `completed` без прохождения `review` и `approved` (для задач с кодом — плюс зелёный CI).

## 3. Протокол Codex ↔ Claude

### Режимы

| Режим | Когда | Схема |
|---|---|---|
| **SOLO** | тривиальная задача | один исполнитель → review другим |
| **PAIR** | сложное архитектурное решение | оба получают задачу, обмениваются структурированными артефактами через orchestrator (максимум 3 раунда), затем один пишет код, второй review |
| **PARALLEL** | независимые части одной задачи | AI CTO декомпозирует: Codex → backend, Claude → frontend; merge после обоюдного CI |
| **REVIEW** | стандартный поток | один пишет, другой независимо проверяет по рубрике |
| **COMPETE** | неочевидная проблема с развилкой решений | оба независимо предлагают решение + обоснование; Auditor (третья модель, класс strong) выбирает по рубрике; проигравший вариант архивируется в `decisions` |

Выбор режима — поле `mode` в задаче, ставит AI CTO по правилам: безопасность/деньги → минимум REVIEW; архитектура → PAIR; большая задача с чистым разрезом → PARALLEL; «не знаем как» → COMPETE.

### Технический поток (coding task)

```
TASK (orchestrator)
  → AI CTO: декомпозиция, выбор режима, подзадачи
  → orchestrator создаёт worktrees:
      /srv/worktrees/<TASK_ID>/codex   (branch task/<ID>-codex)
      /srv/worktrees/<TASK_ID>/claude  (branch task/<ID>-claude)
  → исполнители работают параллельно в своих worktrees
  → каждый возвращает report.json + patch (git diff / ветка)
  → cross-review: reviewer получает patch + acceptance_criteria + контекст,
    выдаёт {verdict: approve|request_changes, findings[]}
  → request_changes → статус rework, findings возвращаются автору (≤2 циклов, затем эскалация к AI CTO)
  → approve → merge request → CI (lint, typecheck, unit, integration)
  → staging deploy (автоматически) → browser/integration tests на staging
  → security review (для кода, трогающего auth/payments/permissions — обязательно человек или dedicated Security Reviewer agent с отдельной моделью)
  → approval при необходимости → production deploy через broker → healthcheck
  → task completed, audit закрыт
```

### Правила взаимодействия

1. Агенты **не общаются друг с другом напрямую**. Весь обмен — артефакты через orchestrator (файлы в общем read-only exchange bucket задачи + поля report.json). Это исключает бесконечный диалог и сохраняет аудит.
2. PAIR ограничен 3 раундами обмена; если консенсуса нет — эскалация к AI CTO, который фиксирует решение в `decisions`.
3. Reviewer видит patch и критерии, но не видит рассуждений автора — независимость оценки.
4. COMPETE: авторы не видят решений друг друга до сдачи (orchestrator выдаёт артефакты auditor'у одновременно).

### Рубрика cross-review

Каждый finding: `{severity: blocker|major|minor, file, lines, issue, suggestion}`. Verdict `approve` возможен только при отсутствии blocker/major. Reviewer обязан проверить: соответствие acceptance criteria, корректность тестов (не «пустышки»), отсутствие секретов, отсутствие незапрошенных изменений вне scope задачи.

## 4. Где LLM, а где обычный код

Оркестраторная логика — **код, не LLM**: статусная машина, ретраи, таймауты, выбор следующего шага workflow по DAG, расчёт стоимости, ACL. LLM принимает решения только там, где нужна семантика: декомпозиция задачи, выбор режима, ревью, выбор в COMPETE. Это принципиально: детерминированная часть системы не должна галлюцинировать.
