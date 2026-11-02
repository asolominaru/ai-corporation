# Founder AI OS — ядро v0

Реализация этапа 0 [AI Corporation Blueprint v1](../10_Blueprint/AI_Corporation_Blueprint_v1.md).
Первый tenant — КОРПОРАЦИЯ Анастасии Соломиной (шесть направлений по решению от 26.10.2026).

Стек: Node.js ≥ 22.13, `node:sqlite`, без npm-зависимостей. Локальный однопользовательский пилот.

## Что уже работает

- **Tenant-конфиг** `config/company.json` — компания как код: направления, границы данных, действия только для человека.
- **Реестр ролей** `org/agents.json` — 11 ролей с контрактами и независимыми проверяющими.
- **Task Protocol v1** `schemas/task.schema.json` — единый формат задачи; задачи вида «изучи что-нибудь» отклоняются.
- **Журнал** `src/board.mjs` — SQLite (WAL), цикл ready → running → review → accepted / changes_requested, приёмка артефакта по sha256, защита от устаревшего решения и подмены копии, этап **human approval** для рискованных задач (pending_owner → approve/reject владельца).
- **Model Router** `config/model-router.json` — конфигурация классов задач и политики данных (автоматическая маршрутизация — позже).
- **Blueprints** `blueprints/` — переносимые рецепты: business-community, expert-business, ai-startup.

## Команды

```bash
npm test                                   # 15 тестов ядра
npm run board -- list [project]            # задачи (все или по направлению)
npm run board -- pending                   # что ждёт решения владельца
npm run board -- add backlog/TASK.json     # новая задача по протоколу
npm run board -- start TASK-ID
npm run board -- submit TASK-ID outputs/файл.md
npm run board -- review TASK-ID ROLE SHA256 accepted|changes_requested ПРИЧИНА
npm run board -- approve TASK-ID КОММЕНТАРИЙ   # для задач с human_approval
npm run board -- reject TASK-ID КОММЕНТАРИЙ
npm run board -- events TASK-ID            # история событий
```

Статус `accepted` означает принятие текстового результата независимым проверяющим — не запуск продукта, продажи или публикацию.

## Границы v0

Нет автономного исполнителя, платных вызовов моделей (budget null), многопользовательского доступа, n8n и коннекторов. Это журнал доверенного локального оператора, а не работающая компания 24/7.

## Дальше по дорожной карте

Этап 1 — экран состояния для владельца. Этап 2 — Codex/Claude workers на KZ-сервере с режимами PAIR/PARALLEL/COMPETE/REVIEW. Этап 3 — воронка продаж. Полная карта — в Blueprint v1, §11.
