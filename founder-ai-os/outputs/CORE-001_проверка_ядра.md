# CORE-001 — проверка ядра Founder AI OS v0

Дата: 02.11.2026. Исполнитель: AICEO (в текущем сеансе). Проверяющий: AUD.

## Что реализовано

- Tenant-конфиг `config/company.json`: шесть направлений по решению владельца от 26.10.2026 + служебный проект `core`.
- Реестр ролей `org/agents.json`: 11 ролей Blueprint v1 с контрактами (входы, выходы, инструменты, классы данных, независимый проверяющий).
- Task Protocol v1 (`schemas/task.schema.json`): id, project, goal, why, inputs, expected_output, criteria, mode, budget, deadline, owner, reviewer, human_approval, next_action.
- Журнал `src/board.mjs`: SQLite (WAL), жизненный цикл ready → running → review → accepted / changes_requested, приёмка по sha256, защита от устаревшего решения и подмены артефакта, этап human approval (pending_owner → approve/reject владельца), журнал событий.

## Результаты тестов

`npm test` — 15/15 пройдено (node --test, Node v24.22.1): валидация протокола, контракты ролей, запрет самопроверки, цикл сдачи и приёмки, обнаружение подмены артефакта, human approval.

## Границы v0 (честно)

- Исполнение задач — агентами текущих сеансов; автономных workers нет.
- Платные вызовы моделей заблокированы (budget null); лимит не задан владельцем.
- Один writer, один хост, локальный доверенный оператор; multi-tenant — только конфигурационно.
- Не подключены: n8n, Model Router, Development Workers, RU-сервер, коннекторы.
