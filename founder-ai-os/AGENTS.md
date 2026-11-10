# AGENTS.md — правила для AI-агентов в этом репозитории

Этот файл обязателен к прочтению любым AI-агентом (Codex, Claude Code, другие), работающим с кодовой базой. Действует над всем деревом `founder-ai-os/`.

## Иерархия

Владелец (Анастасия) → AI CEO → департаменты. Владелец находится НАД конвейером, не внутри него.

## Законы проекта

1. **Не создавай функцию, пока не понятно, какую дорогую работу она заменяет или какой доход создаёт.**
2. Задачи — только по `schemas/task.schema.json` (v2). «Изучи и предложи что-нибудь» запрещено.
3. Исполнитель и проверяющий — всегда разные роли. Ревью кода — не автором кода. Code review — не той моделью, что писала код.
4. Решение по артефакту принимается по sha256 просмотренной версии.
5. `accepted` = принят текстовый результат, не запуск продукта/продаж/публикации.
6. Рискованные действия (см. `requires_human_approval` в task.schema.json и `blueprints/company.yaml → approval_policies`) — только с подтверждением владельца.
7. Платные вызовы моделей заблокированы, пока бюджет задачи не задан (null = стоп).
8. Конфиденциальные и персональные данные — только утверждённый контур (privacy class в model-router). Содержимое частных консультаций — никогда.
9. Production: только Git → тесты → review → staging → approval → deploy → healthcheck. Модели не получают root. Никогда.
10. Прохождение тестов не называть аудитом безопасности.

## Жёсткие правила работы с кодом

1. **Работай только в выделенном git worktree.** Никогда не редактируй чужую рабочую копию и `main` напрямую.
2. **Одна задача — одна ветка — один merge request.** Имя ветки: `task/<TASK_ID>-<slug>`.
3. **Никаких секретов в коде.** Ни ключей, ни токенов, ни паролей — даже «временно». Обнаруженный секрет в истории = инцидент безопасности.
4. **Definition of Done** (без исключений): acceptance criteria выполнены; lint PASS; typecheck PASS; unit tests PASS; integration tests PASS; security review выполнен; migration применима вперёд и откатываема; changelog обновлён.
5. **Запрещено** самостоятельно: менять CI/CD, инфраструктуру production, auth, DNS, схему production-БД деструктивно, permissions. Это зона human approval.
6. Если задача не может быть завершена — статус `blocked` с причиной и списком разблокировки. Никаких «почти готово».
7. Архитектурные изменения — только через ADR в `docs/adr/`.

## Отчёт после каждой задачи

`report.json` (машинный, формат — docs/TASK_PROTOCOL.md §3) + человекочитаемый блок:

WHAT_CHANGED / FILES_CHANGED / TEST_RESULTS / RISKS / KNOWN_ISSUES / NEXT_STEP

## Границы доступа

| Зона | Доступ агента |
|---|---|
| Код в своём worktree | read/write |
| Другие worktrees | нет |
| `data/` (SQLite, неизменяемые артефакты) | read; не редактировать вручную |
| Staging | через deploy-broker, после зелёных тестов |
| Production RU | никогда напрямую; только задача на deploy через approval |
| PostgreSQL control-plane | только через backend API, по своим permissions |
| Knowledge base | только документы, разрешённые роли |

## Структура репозитория

- `config/` — tenant и model router (компания как код)
- `org/agents.json` — роли и контракты ядра v0
- `blueprints/` — переносимые рецепты компаний (company.yaml + agents/)
- `schemas/` — протоколы (task v2 — канонический; task-v1 — для ядра v0)
- `services/`, `apps/`, `packages/` — код платформы (по мере реализации)
- `src/` — ядро v0 (журнал, board.mjs)
- `backlog/` — задачи JSON; `outputs/` — результаты Markdown
- `infra/` — docker, bootstrap, мониторинг
- `docs/` — архитектура, ADR, provenance

## Контекст проекта

- Архитектура: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Протокол задач: [docs/TASK_PROTOCOL.md](docs/TASK_PROTOCOL.md)
- Безопасность: [docs/SECURITY.md](docs/SECURITY.md)
