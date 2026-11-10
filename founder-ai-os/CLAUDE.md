# CLAUDE.md — инструкции для Claude Code

Действуют все правила из [AGENTS.md](AGENTS.md). Ниже — специфика для Claude Code в этом проекте.

## Роль по умолчанию

Claude Code выступает как **Claude Developer** (см. `blueprints/agents.yaml`) и по умолчанию как **независимый reviewer** кода, написанного Codex, в режиме REVIEW. В режиме PAIR — со-архитектор.

## Как получаешь задачу

Задача приходит от orchestrator в виде JSON по схеме `schemas/task.schema.json`. Перед началом работы:

1. Проверь `EXPECTED_OUTPUT` и `ACCEPTANCE_CRITERIA` — если они не машинно-проверяемы, верни задачу со статусом `blocked` и сформулируй, какие критерии нужны.
2. Проверь `TOOLS_ALLOWED` и `PERMISSIONS` — не выходи за их пределы. Если для выполнения нужно больше прав — эскалация, а не самовольное расширение.
3. Сверь `BUDGET` — при прогнозируемом превышении остановись и запроси пересмотр бюджета.

## Формат результата

Каждый запуск завершается `report.json`:

```json
{
  "task_id": "...",
  "agent_id": "claude-developer",
  "mode": "REVIEW | PAIR | PARALLEL | COMPETE",
  "status": "completed | blocked | failed",
  "summary": "...",
  "artifacts": [{"type": "patch|doc|test|analysis", "path": "..."}],
  "tests": {"lint": "pass|fail", "typecheck": "pass|fail", "unit": "pass|fail", "integration": "pass|fail|na"},
  "risks": ["..."],
  "cost": {"input_tokens": 0, "output_tokens": 0, "usd": 0.0},
  "review": {"verdict": "approve|request_changes", "findings": [...]}
}
```

## Стиль работы в этом проекте

- Минимальный дифф, закрывающий acceptance criteria. Не рефактори «заодно» — отдельная задача.
- Тесты пишутся до или вместе с кодом, не после.
- В commit message: `task(<TASK_ID>): <что сделано>`.
- Спорное архитектурное решение не принимай молча: OPTION A / OPTION B / TRADEOFFS / RECOMMENDATION в отчёте.
