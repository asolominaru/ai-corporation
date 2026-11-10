# FOUNDER AI OS

Операционная система цифровой компании с ИИ-сотрудниками.
Первый tenant: 5 бизнес-контуров (Личный бренд, Проявленность, Ярдники, ВФОРУМЕ, R&D/Startup Lab).
Архитектура сразу спроектирована как **AI Corporate OS** — переносимая на другие компании без переписывания ядра.

> Главный принцип: ИИ выдаёт не деятельность, а законченный бизнес-результат.
> Второй принцип: сначала устойчивая работающая система для своей компании, потом тиражируемый продукт.

## Ключевые архитектурные решения (summary)

| Решение | Выбор | Почему |
|---|---|---|
| Приватная сеть | **Tailscale** (MVP) → миграционный путь на Headscale | ACL, управление ключами, аудит из коробки; зависимость от чужого control plane нейтрализуется через Headscale в v1.1 |
| Оркестрация | **Собственный backend (FastAPI) + n8n для триггеров/интеграций** | n8n не должен быть мозгом: state, permissions, аудит — только в своём коде |
| Очередь задач | **PostgreSQL `SELECT … FOR UPDATE SKIP LOCKED`** | Минус RabbitMQ/Kafka на MVP; Redis — для кэша и rate limits |
| БД | **PostgreSQL + Row Level Security** для multi-tenant | Одна СУБД, жёсткая изоляция tenant_id на уровне БД, а не приложения |
| Секреты | **SOPS + age** (MVP) → Vault/Infisical позже | Не требует отдельного сервера, секреты зашифрованы в Git безопасно |
| Git | **Monorepo `founder-ai-os` + отдельные репо продуктов (`vforume`) + `infrastructure`** | Параллельная AI-разработка через branches + git worktrees |
| AI-разработка | **Codex + Claude Code в 4 режимах: PAIR / PARALLEL / REVIEW / COMPETE** | Каждый агент — в своём worktree, обмен только через orchestrator и структурированные отчёты |
| Model Router | **Свой слой** поверх OpenAI / Anthropic / Gemini + open-weight | Выбор модели по типу задачи, цене, приватности, историческому eval score |
| Деплой в RU | **deploy-ai user + whitelisted deploy-команды + Tailscale** | AI-агенты никогда не получают root и прямой доступ к RU production |
| Наблюдаемость | **Prometheus + Loki + Grafana + Alertmanager → Telegram** | Минимальный стек, закрывающий logs/metrics/alerts; traces — позже (Tempo) |
| Бэкапы | **restic → off-provider object storage**, WAL-архив PostgreSQL | RPO/RTO по категориям — см. docs/DISASTER_RECOVERY.md |

## Структура репозитория

```
/founder-ai-os
  /apps            # пользовательские приложения (CEO Dashboard, admin UI)
  /services        # backend services (orchestrator, model-router, knowledge, deploy-broker)
  /agents          # определения AI-сотрудников (agent.yaml), system instructions
  /workflows       # workflow.yaml — машинно-исполняемые процессы
  /connectors      # connector manifests + adapters (gmail, gdrive, telegram, github, ssh…)
  /models          # model registry, pricing table, eval results
  /blueprints      # company.yaml / department.yaml — развёртывание компании из шаблона
  /policies        # approval policies, RBAC, budget guards
  /schemas         # JSON Schema: task, agent, workflow, connector, blueprint
  /packages        # shared libraries (schemas, clients, utils)
  /infra           # docker, ansible, systemd, bootstrap, monitoring
  /scripts         # операционные скрипты
  /docs            # вся проектная документация
  /tests           # unit / integration / e2e / acceptance
```

## Документация

| Документ | Содержание |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архитектура, Mermaid-диаграммы, топология ES/KZ/RU, сеть, Docker Compose, environments |
| [docs/DATABASE.md](docs/DATABASE.md) | ER-модель PostgreSQL, tenant isolation, индексы |
| [docs/TASK_PROTOCOL.md](docs/TASK_PROTOCOL.md) | Протокол задач, статусная машина, протокол Codex↔Claude |
| [docs/SECURITY.md](docs/SECURITY.md) | RBAC, секреты, human approval, аудит, защита от prompt injection, Security Center / AI CISO |
| [docs/EDITORIAL.md](docs/EDITORIAL.md) | AI-редакция «Сила малых групп» (P1): конвейер, роли, календарь, content score, anti-AI filter, конфиденциальность |
| [docs/CONTROL_TOWER.md](docs/CONTROL_TOWER.md) | Founder Control Tower (5 уровней), Incident Center, observability-стек, первый показатель успеха |
| [docs/GOVERNANCE.md](docs/GOVERNANCE.md) | Weekly Executive Meeting (money-first), Decision Pack, принцип управления исключениями |
| [docs/FINANCE.md](docs/FINANCE.md) | Financial Decision System: management P&L, 13-week cash flow, time & attention ledger, unit economics, kill rules |
| [docs/REVENUE_SYSTEM.md](docs/REVENUE_SYSTEM.md) | Центральный цикл: customer intelligence → positioning → marketing → value selling → RevOps |
| [docs/COUNCILS.md](docs/COUNCILS.md) | Четыре совета (Executive / Entrepreneurial / Creative / Risk-Audit), оптики на публичных источниках |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment flow, порядок установки, список credentials |
| [docs/DISASTER_RECOVERY.md](docs/DISASTER_RECOVERY.md) | Бэкапы, RPO/RTO, процедура восстановления |
| [docs/ROADMAP.md](docs/ROADMAP.md) | MVP scope, роадмап, чек-листы, смета, план масштабирования |
| [docs/RED_TEAM_REVIEW.md](docs/RED_TEAM_REVIEW.md) | Критический разбор собственной архитектуры с исправлениями |
| [docs/FINAL_ANSWERS.md](docs/FINAL_ANSWERS.md) | Ответы на три контрольных вопроса (переносимость, замена моделей, потеря Spain-node) |

## Статус и существующее ядро v0

Версия 0.1 (draft для независимой проверки). Секретов в репозитории нет и быть не должно — все чувствительные значения через SOPS, шаблоны в `.env.example`.

В репозитории уже существует **локальный пилот ядра v0** (коммит от 2026-11-02), созданный ранее Codex-сессией: `src/board.mjs` (журнал задач на SQLite), `org/agents.json` (роли и контракты), `config/company.json` + `config/model-router.json` (компания как код), `backlog/CORE-001.json`, `docs/adr/ADR-001-core-v0.md`, `docs/provenance.md`. Это рабочий локальный пилот с правильными принципами (budget null = блок, исполнитель ≠ проверяющий).

Отношение v0 → v1:
- v0 остаётся источником истины по **орг-контрактам и законам** до миграции в blueprints/.
- Протокол задач v2 (`schemas/task.schema.json`) расширяет v1 (`schemas/task-v1.schema.json`): добавлены tenant_id, acceptance_criteria как массив машинно-проверяемых проверок, статусная машина, retry/escalation. Миграция backlog из v1 в v2 — отдельная задача фазы 0.
- Целевая платформа (orchestrator + model router + PostgreSQL) описана в docs/ и заменяет SQLite-журнал v0 в фазе 1.
