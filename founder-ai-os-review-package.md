# FOUNDER AI OS — полный пакет для независимой проверки
Собрано: 2026-11-05
Состав: вся документация, все схемы, blueprints, workflows, infra bootstrap.
Секретов в пакете нет (все значения — плейсхолдеры __SOPS__).


================================================================================
# ФАЙЛ: README.md
================================================================================

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


================================================================================
# ФАЙЛ: AGENTS.md
================================================================================

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


================================================================================
# ФАЙЛ: CLAUDE.md
================================================================================

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


================================================================================
# ФАЙЛ: docs/ARCHITECTURE.md
================================================================================

# ARCHITECTURE.md

## 1. Executive architecture summary

Founder AI OS — производственная система, а не чат с агентами. Единый контур:

```
Событие → Задача → Декомпозиция → Исполнитель → Инструменты → Результат
→ Независимая проверка → Acceptance test → Approval → Следующий workflow → KPI → Audit log
```

Ядро — **orchestrator service** (FastAPI, Python): владеет состоянием задач, агентов, permissions, аудитом, маршрутизацией моделей и approvals. Вокруг него:

- **PostgreSQL** — единственный source of truth (данные, очередь задач через `SKIP LOCKED`, audit log).
- **Redis** — кэш, rate limits, ephemeral state. Не source of truth.
- **n8n** — только event triggers и интеграции (входящие webhook, почта, календарь). Не хранит бизнес-состояния.
- **Model Router** — единая точка вызова LLM; провайдеры взаимозаменяемы.
- **AI-агенты** (Codex, Claude Code, др.) — stateless исполнители, запускаемые orchestrator'ом в изолированных git worktrees.
- **Knowledge layer** — ingestion → chunking → embeddings (pgvector) → retrieval с фильтрацией по правам роли.
- **Deploy broker** — единственный путь к RU production.

Система multi-tenant с рождения: `tenant_id` + PostgreSQL Row Level Security на каждой бизнес-таблице.

## 2. Общая архитектура (Mermaid)

```mermaid
flowchart TB
    subgraph EXT[Внешний мир]
        TG[Telegram]
        GM[Gmail]
        GD[Google Drive]
        GH[GitHub]
        WH[Webhooks]
    end

    subgraph SPAIN[SPAIN — Primary AI / Control Node]
        N8N[n8n — triggers & integrations]
        ORCH[Orchestrator API<br/>FastAPI]
        MR[Model Router]
        AGW[Agent Workers<br/>Codex / Claude Code<br/>в git worktrees]
        PG[(PostgreSQL<br/>control-plane + queue + RLS)]
        RD[(Redis)]
        KNOW[Knowledge Service<br/>pgvector]
        MON[Prometheus + Grafana + Loki]
        N8N -->|events| ORCH
        ORCH --> MR
        ORCH --> AGW
        ORCH --> PG
        ORCH --> RD
        ORCH --> KNOW
        AGW --> PG
    end

    subgraph LLM[AI Providers]
        OAI[OpenAI]
        ANT[Anthropic]
        GEM[Google Gemini]
        OW[Open-weight / Qwen / DeepSeek / Kimi]
    end

    subgraph KZ[KAZAKHSTAN — Warm Standby]
        KZREPL[Replica set:<br/>config, git mirror,<br/>docker images, backups]
    end

    subgraph RU[RUSSIA — Production Node]
        RP[Reverse Proxy]
        VF[ВФОРУМЕ + сайты + API]
        PGDB[(Production DB<br/>данные РФ)]
        DBRK[Deploy Broker<br/>deploy-ai user]
    end

    EXT --> N8N
    MR --> OAI & ANT & GEM & OW
    ORCH -->|репликация конфигов, бэкапы| KZREPL
    ORCH -->|deploy задача + approval| DBRK --> VF
    GH --> AGW
    MON -.->|alerts| TG
```

## 3. Deployment topology: Spain / Kazakhstan / Russia

### Spain — PRIMARY AI NODE
| Компонент | Назначение |
|---|---|
| Orchestrator API | состояние задач, агентов, approvals, аудит |
| Model Router | маршрутизация LLM-вызовов, cost tracking |
| Agent Workers | Codex CLI, Claude Code CLI в worktrees |
| n8n | triggers, интеграции |
| PostgreSQL | control-plane, очередь, аудит |
| Redis | кэш, rate limit |
| Knowledge service | pgvector retrieval |
| Monitoring | Prometheus, Loki, Grafana, Alertmanager |
| restic | бэкапы в off-provider storage |

Требования к VPS: 4 vCPU / 8–16 GB RAM / 160 GB SSD (Hetzner/другой EU-провайдер, ~€15–30/мес).

### Kazakhstan — SECONDARY NODE (warm standby)
Получает непрерывно:
- git-зеркала всех репозиториев (push в 2 remote);
- PostgreSQL WAL-архив + nightly base backup (restic);
- docker images (registry mirror или `docker save` по расписанию);
- конфигурацию (SOPS-зашифрованную, ключ age у владельца + escrow);
- IaC (те же install-скрипты, что и для Spain).

Не держит живой трафик. Процедура активации — docs/DISASTER_RECOVERY.md §4. RTO для control-plane: ≤ 4 часа при отработанной процедуре.

### Russia — PRODUCTION NODE
- Только runtime для российских пользователей: ВФОРУМЕ, сайты, API, production DB (данные, которые по 152-ФЗ должны быть в РФ, — физически здесь).
- Никаких LLM-клиентов, никаких unrestricted shells для AI.
- Вход: только Tailscale + reverse proxy.
- Deploy — исключительно через deploy broker (см. docs/SECURITY.md §6).

## 4. Network architecture: Tailscale vs native WireGuard

| Критерий | Tailscale | Native WireGuard |
|---|---|---|
| Безопасность | WireGuard-транспорт + SSO-идентичность узлов, ACL как код | Тот же транспорт, но ключи и ACL — руками |
| Сложность | Низкая: установка за минуты | Средняя: ручная раздача ключей, peer-конфиги N×N |
| Управление ключами | Автоматическая ротация, привязка к identity | Полностью ручная; компрометация ключа = ручная ротация на всех узлах |
| ACL | Централизованные, group/tag-based, в Git (infra as code) | Только firewall поверх — iptables/nftables |
| Disaster recovery | Переустановка узла = tailscale up + auth key | Восстановление = восстановление конфигов и ключей вручную |
| Независимость от стороннего control plane | **Зависимость** (coordination server Tailscale). Смягчается: coordination нужен только для установления соединения и ротации ключей, не для трафика (direct P2P) | Полная независимость |
| Обслуживание | Минимальное | Растёт с числом узлов |

**Решение для MVP: Tailscale.**

Обоснование: 3 узла + ноутбук владельца + CI; скорость развёртывания и качество ACL важнее идеологической независимости. Риск зависимости от control plane реальный, но ограниченный: при недоступности coordination server уже установленные P2P-соединения продолжают работать; риск — невозможность добавить новый узел.

**Миграционный путь (v1.1):** self-hosted Headscale как control plane — тот же клиент, своя координация, размещается на KZ-node. Это закрывает и vendor lock-in, и DR-сценарий.

### Схема сети

```mermaid
flowchart LR
    subgraph TAILNET[tailnet: founder-ai]
        direction LR
        ES[es-node<br/>100.64.0.10<br/>tag:control]
        KZ[kz-node<br/>100.64.0.20<br/>tag:standby]
        RU[ru-node<br/>100.64.0.30<br/>tag:production]
        NB[owner-laptop<br/>tag:admin]
        CI[ci-runner<br/>tag:ci]
    end
    ES -->|5432,6379 only tag:control| ES
    KZ -->|pull backups/config from ES| ES
    ES -->|deploy-broker SSH :22| RU
    NB -->|SSH admin| ES & KZ & RU
    CI -->|SSH deploy-staging| ES
```

ACL-принципы:
- `tag:production` принимает соединения только от deploy-broker (ES) по порту 22 и от monitoring (ES) по 9100/9113.
- `tag:standby` — только исходящие к ES (pull-модель: KZ сам забирает бэкапы; ES не имеет права писать в KZ).
- Никакой узел tailnet не exposed в публичный интернет, кроме RU reverse proxy (80/443) и Spain API (443, за прокси с auth).

## 5. Docker Compose architecture (Spain)

Один `docker-compose.yml` на узел, профили для необязательных сервисов. Сервисы:

| Сервис | Образ | Назначение |
|---|---|---|
| `postgres` | postgres:16 + pgvector | control-plane, queue, knowledge |
| `redis` | redis:7 | кэш, rate limits |
| `orchestrator` | свой образ | FastAPI backend |
| `model-router` | свой образ | LLM gateway + cost metering |
| `knowledge` | свой образ | ingestion/retrieval |
| `n8n` | n8nio/n8n | triggers/интеграции |
| `agent-runner` | свой образ | исполнитель Codex/Claude CLI в worktrees (docker-outside-docker через контролируемый socket proxy) |
| `deploy-broker` | свой образ | единственный клиент SSH к RU |
| `prometheus`, `grafana`, `loki`, `promtail` | официальные | observability |
| `node-exporter`, `cadvisor` | официальные | метрики хоста |
| `restic` | restic/restic | бэкапы по cron |
| `caddy` | caddy:2 | TLS, reverse proxy, auth для admin-интерфейсов |

Файл: [infra/docker-compose.yml](../infra/docker-compose.yml).

## 6. Environment strategy

| Env | Где | Данные | Доступ |
|---|---|---|---|
| dev | ноутбуки / worktrees на Spain | синтетические | разработчики и AI-агенты |
| test | CI runner на Spain | синтетические + fixtures | CI |
| staging | Spain, отдельный compose-проект, отдельная БД | обезличенная копия (скрипт anonymize) | AI-агенты через deploy-broker, владелец |
| production | RU (продукты), Spain (control-plane) | реальные | минимальный, через approval |

Правила:
- Один и тот же образ проходит dev → test → staging → production без пересборки (build once, promote by tag).
- Миграции БД применяются на staging первыми, затем на production через ту же команду.
- Секреты разделены по env: отдельные age-получатели в SOPS для staging и production.

## 7. Model Router design

Единственный способ вызвать LLM в системе — через Model Router. Прямые вызовы API из агентов запрещены политикой.

### Вход решения

```json
{
  "task_type": "backend_coding | frontend_coding | research | classification | writing | review | decision_analysis",
  "quality_required": "low | standard | high | critical",
  "privacy_level": "public | internal | confidential",
  "latency_budget_ms": 30000,
  "context_size_estimate": 45000,
  "max_cost_usd": 0.50,
  "tenant_id": "..."
}
```

### Логика выбора (по приоритету)

1. **Privacy filter.** `confidential` → только провайдеры с zero-retention соглашением или open-weight локально. Данные РФ-пользователей — не покидают разрешённый контур.
2. **Context filter.** Отсекает модели с недостаточным окном.
3. **Availability.** Живой health-check + circuit breaker per provider.
4. **Score.** `score = w1·eval_score(task_type, model) + w2·(1/price) + w3·(1/latency)` — веса в конфиге, `eval_score` из таблицы `model_runs` (см. раздел 8).
5. **Fallback chain.** primary → fallback по списку, максимум 2 ретрая с exponential backoff.

### Реестр моделей

`models/registry.yaml` — единственное место, где описаны модели: id, провайдер, endpoint, цены, окно контекста, лимиты, privacy class. Добавление Qwen/DeepSeek/Kimi = новая запись в реестре + адаптер интерфейса провайдера, без изменения бизнес-логики.

### Актуальные цены (проверено 2026-11-05, на 1M токенов input/output)

| Класс | Модель | Цена | Применение |
|---|---|---|---|
| Frontier | Claude Fable 5.1, GPT-6 Astra | $10 / $50 | COMPETE-арбитраж, критичные решения — редко |
| Strong | Claude Opus 5.5, GPT-5.6 Sol | $4 / $20 | сложная архитектура, review критичного кода |
| Mid | Claude Sonnet 5.5, GPT-6.1 Sol, Gemini 4 Argon* | $2 / $10 | основной coding/research workhorse |
| Fast | Gemini 3.8 Flash** | $0.75 / $3.75 | drafts, summarization |
| Cheap | Claude Haiku 5.5, GPT-6 Luna, Gemini 3.5 Flash-Lite | $0.10–0.30 / $0.50–2.50 | классификация, routing, extraction |

\* Argon: $2/$10 до 30.11.2026, с 01.12.2026 — $4/$20. В смете считаем по цене после повышения.
\** Flash: с 01.01.2027 — $1.50/$7.50.

Правило из ТЗ зашито в policy: задача типа `classification` никогда не получает модель класса выше `cheap`.

## 8. Model evaluation / internal arena

Каждый LLM-вызов пишется в `model_runs`: task_type, model, cost, latency, success, downstream review score, acceptance result, human correction flag. Раз в неделю агрегация → таблица эффективности по (task_type × model), которую читает router.

Режим COMPETE (см. TASK_PROTOCOL.md) одновременно является источником arena-данных: два агента решают одну проблему независимо, auditor оценивает оба решения по рубрике — результат ложится в `model_runs.review_score`.

## 9. Knowledge layer

```
sources (GDrive, docs, transcripts, CRM, git)
  → ingestion workers (connectors)
  → parsing (text/markdown/pdf)
  → metadata (tenant_id, acl_tags, source, date)
  → chunking (semantic, ~500 токенов, overlap 10%)
  → embeddings (pgvector, HNSW index)
  → retrieval: WHERE tenant_id = :t AND acl_tags <@ :role_tags
```

**Правило:** retrieval-запрос всегда несёт `role_tags` вызывающего агента; фильтрация на уровне SQL, а не prompt. Общего unrestricted vector store не существует архитектурно — таблица `knowledge_chunks` имеет NOT NULL `acl_tags`, и политика RLS режет строки до similarity search.

## 10. Repository structure & Git architecture

**Решение: monorepo `founder-ai-os` + отдельные репозитории `vforume` и `infrastructure`.**

- OPTION A (всё в одном monorepo) — отвергнут: ВФОРУМЕ — продукт со своим релизным циклом и потенциально другой командой; infrastructure содержит чувствительную конфигурацию с отдельным контуром доступа.
- OPTION B (всё раздельно) — отвергнут: shared schemas/packages, атомарные изменения протоколов, единый CI — всё это сильно дешевле в monorepo.
- TRADEOFF принятого варианта: 3 репозитория вместо 1 — нужна синхронизация версий `packages/schemas` между `founder-ai-os` и `vforume`. Решается публикацией versioned package и dependabot.

### Параллельная AI-разработка

- Каждая задача → ветка `task/<TASK_ID>-<slug>` → отдельный `git worktree` в `/srv/worktrees/<TASK_ID>/`.
- Codex и Claude никогда не разделяют рабочую копию.
- Merge — только через MR с зелёным CI и cross-review (см. TASK_PROTOCOL.md).
- `main` защищён: push запрещён всем, включая владельца, кроме merge через CI.


================================================================================
# ФАЙЛ: docs/DATABASE.md
================================================================================

# DATABASE.md — PostgreSQL ER-модель

## Принципы

1. PostgreSQL 16 — единственный source of truth.
2. **Multi-tenant:** каждая бизнес-таблица имеет `tenant_id uuid NOT NULL REFERENCES tenants(id)` + Row Level Security. Политика: `USING (tenant_id = current_setting('app.tenant_id')::uuid)`. Backend устанавливает `app.tenant_id` на каждое соединение из аутентифицированного контекста. Superuser для приложения не используется; миграции — отдельная роль `migrator`.
3. Миграции — Alembic (Python), одна миграция = одна логическая операция, каждая с `downgrade()`.
4. Аудит и логи стоимости — append-only (REVOKE UPDATE, DELETE).
5. Идентификаторы — `uuid` (gen_random_uuid), время — `timestamptz`.

## ER-диаграмма (ядро)

```mermaid
erDiagram
    tenants ||--o{ business_units : has
    tenants ||--o{ users : has
    tenants ||--o{ agents : has
    business_units ||--o{ departments : contains
    departments ||--o{ projects : owns
    projects ||--o{ products : ships
    projects ||--o{ tasks : contains
    agents ||--o{ task_runs : executes
    tasks ||--o{ task_runs : has
    tasks ||--o{ approvals : requires
    tasks ||--o{ audit_logs : writes
    workflows ||--o{ workflow_runs : instantiates
    workflow_runs ||--o{ tasks : spawns
    models ||--o{ model_runs : billed_in
    task_runs ||--o{ model_runs : consumes
    customers ||--o{ deals : has
    customers ||--o{ leads : source_of
    leads ||--o{ deals : converts_to
    deals ||--o{ deployments : delivered_by
    experiments ||--o{ metrics : measures
    content_items ||--o{ leads : attributes
    incidents ||--o{ audit_logs : correlates
    documents ||--o{ knowledge_items : chunks_into
```

## Таблицы

### Ядро и multi-tenant

**tenants** — компания-арендатор.
Поля: `id, name, slug, status, plan, created_at`.
Индексы: unique(slug).

**users** — люди.
Поля: `id, tenant_id, email, full_name, role_id, status, last_login_at`.
Индексы: unique(tenant_id, email).

**roles / permissions** — RBAC. `roles(id, tenant_id, name, description)`; `permissions(id, code, description)`; связующая `role_permissions(role_id, permission_id)`. Коды permissions — строки вида `deploy.production`, `approve.payment`, `knowledge.read.confidential`.

**business_units** — пять контуров (Личный бренд, Проявленность, Ярдники, ВФОРУМЕ, R&D).
Поля: `id, tenant_id, name, code, owner_user_id`.

**departments** — отделы внутри business unit (Development, Sales, Content, Product, Operations, Client Success, R&D).
Поля: `id, tenant_id, business_unit_id, name, kpi_definition jsonb`.

**projects / products** — `projects(id, tenant_id, department_id, name, status, repo_url)`; `products(id, tenant_id, project_id, name, status, metric_of_success)`.

### Задачи и агенты

**tasks** — см. TASK_PROTOCOL.md; зеркалит JSON Schema.
Поля: `id, tenant_id, project_id, department_id, workflow_run_id, goal, why, input jsonb, context jsonb, expected_output jsonb, acceptance_criteria jsonb, tools_allowed text[], permissions text[], primary_model, fallback_model, budget_usd numeric, deadline timestamptz, reviewer_agent_id, retry_policy jsonb, escalation_policy jsonb, status task_status, parent_task_id, created_by, created_at, updated_at`.
Индексы: `(tenant_id, status)`, `(status) WHERE status = 'queued'` — для SKIP LOCKED-очереди, `(project_id, status)`, partial index по `deadline` для активных.
`task_status` — enum: `created, queued, running, blocked, review, rework, approved, failed, completed, cancelled`.

**task_runs** — один запуск агента по задаче (попытка).
Поля: `id, tenant_id, task_id, agent_id, mode (PAIR|PARALLEL|REVIEW|COMPETE|SOLO), started_at, finished_at, status, report jsonb, cost_usd, tokens_in, tokens_out, worktree_path, branch, commit_sha`.
Индексы: `(task_id, created_at)`, `(agent_id, started_at)`.

**agents** — ИИ-сотрудник (экземпляр роли).
Поля: `id, tenant_id, department_id, role_id, name, system_instruction_ref, tools text[], permissions text[], model_policy jsonb, budget_monthly_usd, kpi jsonb, reviewer_agent_id, escalation_rule jsonb, status`.

**agent_roles** — справочник ролей (AI CTO, Codex Developer…).
Поля: `id, code, name, goal, input_schema jsonb, output_schema jsonb, default_tools text[], default_kpi jsonb`.

**models** — реестр LLM.
Поля: `id, provider, model_name, input_price_usd, output_price_usd, context_window, privacy_class, status, endpoint_config jsonb`.

**model_runs** — каждый вызов LLM (пишется только router'ом).
Поля: `id, tenant_id, task_run_id, model_id, task_type, tokens_in, tokens_out, cost_usd, latency_ms, success bool, review_score numeric, acceptance_result, human_correction bool, created_at`.
Индексы: `(task_type, model_id, created_at)` — для arena-агрегации, `(tenant_id, created_at)` — для cost reporting.
Append-only.

**workflows / workflow_runs** — `workflows(id, tenant_id, code, name, definition jsonb /* DAG шагов */, version)`; `workflow_runs(id, tenant_id, workflow_id, status, started_by, context jsonb, started_at, finished_at)`.

### CRM и продажи

**customers** — `id, tenant_id, name, contacts jsonb, segment, status`.
**leads** — `id, tenant_id, customer_id, source, content_item_id /* атрибуция */, status, qualification jsonb, next_contact_at, probability`.
**deals** — `id, tenant_id, customer_id, lead_id, amount, currency, status (open|won|lost), lost_reason, closed_at`.
Индексы: `leads(tenant_id, status, next_contact_at)`, `deals(tenant_id, status)`.

### Контент, знания, решения

**content_items** — `id, tenant_id, department_id, type, title, body_ref, status, published_at, utm jsonb`.
**documents** — `id, tenant_id, source_connector, external_id, title, acl_tags text[], uri, ingested_at`.
**knowledge_items** — чанки: `id, tenant_id, document_id, chunk_index, content, embedding vector(1536), acl_tags text[] NOT NULL`.
Индексы: HNSW по `embedding`, `(tenant_id) ` + RLS по acl_tags (через дополнительную политику и GIN по acl_tags).
**decisions** — `id, tenant_id, author (agent|user), question, options jsonb, assumptions jsonb, probabilities jsonb, expected_value jsonb, chosen, evidence_that_changes jsonb, created_at` — журнал Decision Science layer.
**approvals** — `id, tenant_id, task_id, type, payload jsonb, status (pending|approved|rejected|expired), requested_at, decided_by, decided_at, expires_at, channel_message_id`. См. SECURITY.md §5.

### Эксперименты, метрики, эксплуатация

**experiments** — R&D-воронка: `id, tenant_id, idea, hypothesis, kill_criteria jsonb, stage, unit_economics jsonb, verdict (scale|kill|pivot), created_at, closed_at`.
**metrics** — `id, tenant_id, entity_type, entity_id, metric_code, value numeric, measured_at`. Индекс `(entity_type, entity_id, metric_code, measured_at)`.
**deployments** — `id, tenant_id, project_id, env, commit_sha, image_tag, status, deployed_by (agent|user|broker), approved_by, healthcheck_result, rollback_of, created_at`.
**incidents** — `id, tenant_id, severity, title, status, detected_by, root_cause, resolved_at`.
**audit_logs** — `id, tenant_id, actor_type, actor_id, action, entity_type, entity_id, payload jsonb, prev_hash, hash, created_at`. Hash-chain: `hash = sha256(prev_hash || canonical(payload))`. Append-only. Индекс `(tenant_id, entity_type, entity_id, created_at)`.
**cost_logs** — `id, tenant_id, entity_type (model_run|task|workflow|department|project), entity_id, cost_type (ai|infra|human_estimate), amount_usd, business_value_usd, created_at`. Индекс `(tenant_id, entity_type, entity_id, created_at)`.

## Финансовый контур (добавлено по §49–55 дополнения; см. FINANCE.md)

**financial_transactions** — единая классификация денег. Поля: `id, tenant_id, business_unit_id, project_id, line_item (revenue|cogs|ai_cost|contractors|human_labour|marketing|sales|infrastructure), direction (inflow|outflow), amount, currency, occurred_at, source (manual|import|auto_cost_logs), external_ref`.
Индексы: `(tenant_id, business_unit_id, occurred_at)`, `(line_item)`. План/факт/forecast — отдельное поле `scenario (plan|fact|forecast)`.

**cash_flow_forecast** — 13-недельный rolling forecast: `id, tenant_id, week_start, scenario (base|negative|upside), line_item, amount, computed_at`. Пересчёт еженедельно workflow'ом.

**project_economics** — карточка экономики проекта: `project_id (PK/FK), revenue_potential, direct_cost, ai_cost, human_hours, founder_hours, expected_margin, actual_margin, payback_weeks, strategic_value, probability_of_success, kill_criteria jsonb, kill_rule_status, updated_at`.

**time_entries** — Time & Attention Ledger: `id, tenant_id, project_id, person_type (founder|top_manager|human|ai_run), hours, source (auto_approval|weekly_poll|manual), occurred_on`. Founder hours по approvals считаются автоматически (timestamps), остальное — еженедельный опрос.

**customer_insights** — см. REVENUE_SYSTEM.md §1: `id, tenant_id, source, segment, problem, frequency, severity, current_solution, willingness_to_pay, evidence_level (single_case|few_cases|pattern), created_at`. Индекс `(tenant_id, segment, evidence_level)`.

**positioning** — карточка продукта: `product_id (PK/FK), icp, jtbd, core_problem, promise, proof, differentiation, alternatives, reasons_to_believe, value_metric, price_logic, status, updated_at`.

**deals.value_hypothesis jsonb** — расширение deals: `current_cost_of_problem, lost_revenue, human_hours, risk, expected_value, payback` (value selling, §61). Предложение клиенту без заполненной value_hypothesis блокируется workflow'ом.

## Что осознанно НЕ делаем в БД v1

- Нет отдельной БД на tenant (shared schema + RLS; dedicated schema/БД — опция для enterprise-tenant позже, слой миграций это допускает).
- Нет event sourcing: аудит — append-only лог, но состояние — обычные таблицы. Event sourcing — двойная стоимость записи без пользы на MVP.
- Нет отдельного vector store (Qdrant/Weaviate): pgvector закрывает объёмы MVP (до единиц миллионов чанков) и убирает целый сервис из эксплуатации.
- Нет банковских интеграций: financial_transactions на MVP наполняются импортом/ручным вводом; автоматическая строка — только AI costs из cost_logs.


================================================================================
# ФАЙЛ: docs/TASK_PROTOCOL.md
================================================================================

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


================================================================================
# ФАЙЛ: docs/SECURITY.md
================================================================================

# SECURITY.md — архитектура безопасности

Принцип: AI-агент — не доверенный субъект, а привилегированный процесс с минимальными правами, полным аудитом и невозможностью самостоятельно расширить свои полномочия.

## 1. Модель доступа (RBAC + least privilege)

- Иерархия: Tenant → Business Unit → Department → Agent. Permission проверяется на каждом уровне.
- Permission codes — явные строки (`deploy.production`, `crm.write`, `knowledge.read.confidential`). Никаких «роль=всё».
- Агент получает permission только через `agent.yaml` → таблицу `agents.permissions`. Сам себе агент permission выдать не может — изменение `agents.permissions` требует permission `agent.admin` (только у владельца).
- Токены сервисов: короткоживущие JWT (15 мин), выдаются orchestrator'ом на конкретный `task_run`, audience-ограничены.

## 2. Secret management

- **MVP: SOPS + age.** Секреты лежат в Git в зашифрованном виде (`*.enc.yaml`), расшифровка только на целевом узле его ключом.
- Три age-ключа: `spain`, `kazakhstan`, `russia`. Каждый узел расшифровывает только свой контур.
- Мастер-ключ владельца — офлайн (USB + бумажная копия в сейфе), escrow-копия у доверенного лица.
- API-ключи LLM-провайдеров живут только на Spain (и в зашифрованном виде для KZ-активации). RU-узел не имеет ни одного LLM-ключа.
- Ротация: LLM-ключи — 90 дней, SSH-ключи deploy — 180 дней, age-ключи — при компрометации или раз в год.
- Детекция утечек: pre-commit hook `gitleaks` + тот же сканер в CI. Найденный секрет в истории = немедленная ротация + инцидент.

## 3. SSH и доступ к узлам

- Только ключи, `PasswordAuthentication no`, root login запрещён.
- Пользователи: `ops` (человек-админ), `deploy-ai` (ограниченный деплой), `monitor` (read-only метрики).
- `deploy-ai` не имеет shell-доступа произвольной формы: SSH forced command → `/usr/local/bin/deploy-broker-exec`, который принимает только whitelisted команды (`deploy <project> <image_tag>`, `rollback <project>`, `healthcheck <project>`), валидирует аргументы по regex и логирует каждый вызов.
- Весь SSH-трафик — только внутри tailnet.

## 4. Защита от prompt injection и tool abuse

Угроза реальная: агент читает внешний контент (лиды, письма, веб) — этот контент может содержать инструкции.

Меры:
1. **Изоляция по правам, а не по промптам.** Даже успешно «загипнотизированный» агент физически не может вызвать инструмент вне `tools_allowed` — enforcement на уровне orchestrator API, а не system prompt.
2. **Валидация входа инструментов** по JSON Schema до исполнения.
3. **Небезопасные действия требуют approval-токена**, который агент не может сгенерировать (см. §5).
4. Внешний контент помечается `untrusted` в knowledge layer; при retrieval в контекст задачи он оборачивается с явной меткой и запретом исполнять из него инструкции (защита в глубину, не основной барьер).
5. Egress-фильтрация на agent-runner: разрешены только endpoint'ы LLM API, registry и Git-хостинги. Агент не может отправить данные на произвольный хост.

## 5. Human approval

Обязателен для: payments, contracts, деструктивных изменений production DB, DNS, auth-системы, secrets, удаления production-данных, high-risk production deploy, публичных заявлений с репутационным риском.

### Механизм

1. Агент/workflow создаёт запись в `approvals` (type, payload, expires_at — по умолчанию 24ч).
2. Orchestrator отправляет владельцу Telegram-сообщение с кратким содержанием и двумя кнопками. Сообщение содержит ссылку на полный payload (защищённая страница в admin UI).
3. Кнопка шлёт signed callback (HMAC от bot token + approval_id + решение + timestamp). Проверка подписи на backend. Replay защищён: одноразовый nonce + проверка `decided_at IS NULL`.
4. Решение пишется в `approvals` и `audit_logs`. Задача разблокируется или уходит в `rework`.
5. Истёкший approval → статус `expired`, задача в `blocked`. Никаких «молчаливых согласий».
6. Категории `payment` и `destructive_db` — подтверждение кодовой фразой в ответном сообщении (защита от случайного тапа).

## 6. Deploy path в RU production

```
MR merged → CI build image → push registry →
orchestrator создаёт deploy task → (approval если high-risk) →
deploy-broker (Spain) подписывает deploy-запрос → SSH deploy-ai@ru-node →
deploy-broker-exec валидирует и выполняет: pull image, migrate (forward-only), compose up, healthcheck →
результат в deployments + audit_logs → при fail: автоматический rollback на предыдущий image_tag
```

Codex/Claude нигде в этой цепочке не имеют credentials к RU. Они производят код и MR — не деплой.

## 7. Аудит

- `audit_logs` — append-only, hash-chain (каждая запись включает хеш предыдущей → подделка истории детектируется).
- Пишется: создание/смена статуса задачи, каждый tool call агента, каждый approval, каждый deploy, каждое изменение permissions, каждый доступ к `confidential` knowledge.
- Ежесуточно хвост аудита экспортируется в off-provider object storage (WORM-политика bucket'а — object lock).
- Раз в неделю job проверяет целостность hash-chain.

## 8. Network & container isolation

- Три security zone: public (только reverse proxy RU), tailnet (всё внутреннее), host-local (postgres/redis — только docker network, без публикации портов наружу).
- agent-runner: контейнер без `--privileged`, read-only rootfs, tmpfs для /tmp, drop all capabilities, no-new-privileges, egress через squid-allowlist.
- n8n не имеет доступа к сети postgres напрямую — ходит только в orchestrator API.

## 9. Rate limits и budget guards

- Per-agent и per-tenant лимиты: задач/час, LLM-вызовов/час, $/день. Реализация — Redis token bucket, enforcement в orchestrator и model router.
- Дневной бюджет AI-счёта: при 80% — предупреждение в Telegram; при 100% — новые задачи не стартуют (running дорабатывают), требуется action владельца.
- Аномалия трат (spike >3σ от недельного среднего) → автоматический инцидент + pause дорогих workflow.

## 10. Бэкапы и восстановление

См. DISASTER_RECOVERY.md. Здесь только security-аспект: бэкапы шифруются на стороне клиента (restic, AES-256), ключ — отдельный от age, хранится там же, где мастер-ключ. Restore test — обязательная ежемесячная процедура с записью результата в `audit_logs`.

## 11. Security Center и AI CISO (горизонтальный контур)

Security — не функция Development Department, а отдельный горизонтальный контур, контролирующий всю компанию. Роль: **AI CISO** (`blueprints/agents/ai-ciso.yaml`) — не разрабатывает продукт, а защищает систему. Только read-доступы + alerts; remediation — через задачи и approvals, никогда напрямую.

**Security Center видит:** authentication events, permission changes, failed logins, API key usage, SSH events, deploys, production access, unusual model usage, data exports, connector activity, suspicious agent behaviour, prompt injection attempts, backup status, security updates, open vulnerabilities.

**Zero trust:** ни один агент не получает доступ «потому что он наш агент». Каждый доступ определяется кортежем TENANT × ROLE × TASK × TOOL × RESOURCE × ACTION. Примеры:
- Content Writer: читает обезличенную Knowledge Base; не может читать production DB, SSH, secrets, платежи.
- Codex: repo, test env, staging; не может произвольный доступ к production.

**Secret management (усиление §2):** API keys недопустимы в prompt, Git, AGENTS.md, Docker image, логах, чатах. Проверки: gitleaks (pre-commit + CI), скан логов на паттерны ключей, образы собираются без слоёв с секретами (build-time secrets only).

**Agent sandbox:** критичные workers в ограниченной среде — контроль filesystem (read-only rootfs, tmpfs), network (egress allowlist), commands (whitelisted), connectors (per-task grants), time (timeout), cost и tokens (budget guard).

**Prompt injection по каналам** (расширение §4): email, documents, web pages, CRM notes, user-generated files — весь внешний контент помечается `untrusted`, никогда не становится system instruction, исполнение инструментов из него запрещено на уровне orchestrator.

**Security Weekly Report (автоматически, входит в weekly executive meeting):** incidents, vulnerabilities, access anomalies, outdated components, backup failures, unusual AI behaviour, recommended changes. **Critical events не ждут недельного отчёта — немедленный alert.**


================================================================================
# ФАЙЛ: docs/EDITORIAL.md
================================================================================

# EDITORIAL.md — AI-редакция «Сила малых групп»

Бизнес-приоритет №1 (P1 в roadmap). Проект относится к направлению ПРОЯВЛЕННОСТЬ. Это полноценная редакция, а не демонстрация агентов.

## 1. Цель

Постоянно превращать профессиональный опыт Анастасии в сильный авторский контент, который формирует позиционирование и интеллектуальную территорию, привлекает собственников и бизнес-сообщества, приводит клиентов на ретриты, группы и обучение, создаёт материалы будущей книги и методологическую базу, генерирует лиды в CRM.

## 2. Источники и контур конфиденциальности

Источники: Google Drive, голосовые заметки, транскрипты, встречи форум-групп, ретриты, анкеты участников, супервизии, методологические материалы, мысли Анастасии, старые публикации, исследования, кейсы, вопросы участников, конфликты в группах, обратная связь, международные исследования (YPO/EO и смежные практики, психология малых групп, оргпсихология, групповая динамика, product/management research).

**Классификация при ingestion (обязательное поле `privacy_class`):**

| Класс | Примеры | Правило |
|---|---|---|
| public | старые публикации, открытые исследования | любые модели |
| internal | методология, заметки Анастасии, анкеты (обезличенные) | утверждённые API-провайдеры |
| confidential | транскрипты форум-групп, супервизии, кейсы участников | **обезличивание ДО любого LLM-вызова**; модели только privacy_class=confidential-совместимые; публикация данных участника/группы — только с явным разрешением (фиксируется в CRM) |

Обезличивание — детерминированный пайплайн (NER + словари имён + ручная разметка), а не «промпт про анонимизацию». LLM получает уже обезличенный текст. Это принципиально: confidentiality enforced by pipeline, not by prompt.

## 3. Роли — это функции, а не обязательно модели

13 ролей: Editor-in-Chief, Knowledge Miner, Story Miner, Researcher, Methodology Agent, Writer, Editor, Anastasia Voice Agent, Fact Checker, Content Critic, Ethics/Confidentiality Reviewer, Distribution Agent, Growth Analyst.

Маппинг на 7 агентов (разделение контекста и проверки сохраняется, где критично):

| Агент | Роли | Почему вместе / почему раздельно |
|---|---|---|
| `editor-in-chief` | Editor-in-Chief / Content Director | приоритеты, редакционный календарь, приёмка |
| `knowledge-miner` | Knowledge Miner + Story Miner + Researcher | одна функция добычи: факты, истории, исследования |
| `smg-writer` | Writer + Methodology Agent | черновик + методологическая точность |
| `anastasia-voice` | Anastasia Voice Agent + Editor | стилистическая правка голосом Анастасии |
| `quality-critic` | Content Critic + Fact Checker + anti-AI filter | независимая проверка качества; **не та модель, что писала** |
| `confidentiality-reviewer` | Ethics / Confidentiality Reviewer | **отдельный агент всегда**: veto-право, неподотчётен редактору |
| `distribution-growth` | Distribution Agent + Growth Analyst | публикация, CTA, атрибуция, аналитика |

Правило независимости: писатель (`smg-writer`/`anastasia-voice`), критик (`quality-critic`) и проверяющий конфиденциальность (`confidentiality-reviewer`) — три раздельных контура; veto confidentiality-reviewer'а не отменяется никем, кроме собственника.

## 4. Конвейер

```
RAW KNOWLEDGE → INGESTION → CLASSIFICATION (privacy_class, тема, тип)
→ INSIGHT MINING → STORY MINING → RESEARCH → IDEA
→ EDITORIAL PRIORITY (content score) → DRAFT → ANASTASIA VOICE
→ CRITIC → FACT CHECK → CONFIDENTIALITY CHECK → APPROVAL (owner)
→ PUBLICATION → DISTRIBUTION → CTA → CRM → ANALYTICS
```

Workflow: [workflows/editorial-pipeline.yaml](../workflows/editorial-pipeline.yaml).

Approval собственника — обязательный шаг перед публикацией (категория `public_statement`). Редакция готовит материал «под ключ», собственник тратит минуты на approve/edit/reject, а не редактирует сырьё.

## 5. Редакционный календарь

Статусы материала (`content_items.status`, enum):

`idea → research → approved_topic → draft → editing → fact_check → confidentiality_review → owner_review → scheduled → published → measuring → repurpose`

Переходы — только через orchestrator (каждый переход = task или review-результат, всё в аудите). Календарь визуализируется в Control Tower (уровень departments → content).

## 6. Content Score

Для каждого материала на этапе EDITORIAL PRIORITY и после CRITIC:

| Ось | Шкала |
|---|---|
| Originality | 0–10 |
| Expertise Depth | 0–10 |
| Evidence Quality | 0–10 |
| Relevance | 0–10 |
| Emotional Impact | 0–10 |
| Brand Fit | 0–10 |
| Commercial Potential | 0–10 |
| Reputational Risk | 0–10 (обратная: ≥7 → обязательный owner review независимо от остального) |

Score — инструмент приоритизации, не замена человека. Итоговое решение о публикации — всегда за собственником.

## 7. Anti-AI filter

Автоматическая проверка (quality-critic) по чек-листу: ИИ-канцелярит, штампы, банальные выводы, ненужные вводные, искусственный пафос, чрезмерные списки, повторы, нехарактерная для Анастасии лексика, недоказанные заявления.

Реализация: детерминированные проверки (словари штампов, статистика списков/повторов — обычный код) + LLM-оценка (лексика, пафос, банальность). Content Critic имеет право вернуть материал на переработку (статус → `draft`, цикл rework, максимум 2 — дальше эскалация к editor-in-chief).

Калибровка голоса: корпус эталонных текстов Анастасии (10–20 лучших публикаций) лежит в knowledge base с acl_tag `voice-reference`; voice-агент и critic используют его как референс.

## 8. Content Flywheel

Один сильный источник превращается в серию: Telegram post → длинная статья → серия постов → кейсовый материал → короткое видео → сценарий выступления → фрагмент книги → обучающий материал → commercial insight → R&D hypothesis.

Механика: у каждого `content_item` есть `source_id` и `parent_id`. Статус `repurpose` = материал возвращается в календарь как источник нового формата. Метрика flywheel: `assets_per_source` — сколько опубликованных единиц родил один источник (цель ≥ 3).

## 9. Завершённый продукт материала

Не «ИИ написал пост», а **опубликованный качественный материал** с заполненной карточкой:

SOURCE, THEME, AUDIENCE, PRODUCT (ретрит/группа/обучение/книга), FUNNEL_STAGE, CTA, PUBLICATION_DATE, CHANNEL → и после публикации: LEADS, REACTIONS, MEETINGS, PIPELINE, SALES + сохранённый интеллектуальный материал в Knowledge Base.

Атрибуция: каждый CTA — UTM/помеченная ссылка или кодовое слово; lead в CRM несёт `content_item_id`. KPI редакции — leads/meetings/pipeline/revenue, не количество постов.

## 10. MVP-объём редакции (P1)

Честно о том, что входит, а что нет:

**Входит:** ingestion из Google Drive + ручная загрузка транскриптов; обезличивание; классификация; календарь со всеми статусами; конвейер до owner approval; публикация в Telegram (полуавтомат — по approve собственника); карточка результата; базовый content score; anti-AI filter v1.

**Не входит:** авто-публикация в другие каналы, видео, книга как отдельный трек, полная revenue-атрибуция (сначала CTA→lead→CRM, атрибуция продаж — в P3 вместе с Sales). Полный knowledge layer с pgvector — упрощённо: ingestion + metadata + поиск по тегам; embeddings добавляются, когда объём источников превысит возможности тегового поиска.


================================================================================
# ФАЙЛ: docs/CONTROL_TOWER.md
================================================================================

# CONTROL_TOWER.md — Founder Control Tower и observability

## 1. Назначение

Главный визуальный экран управления цифровой компанией. Отвечает за 30 секунд на вопросы: что происходит, где деньги, что работает/не работает, где задержка, где ошибка, какой агент сломался, какой workflow завис, какой сервер недоступен, где растут расходы, какая модель ошибается, какие задачи просрочены, какие решения нужны от собственника.

**Реализация:** собственное веб-приложение `apps/control-tower` (React + TypeScript + Vite), данные — read-only API поверх PostgreSQL + Prometheus. Не Grafana: Grafana остаётся инженерным инструментом, Control Tower — управленческим. Обоснование: Grafana плохо показывает бизнес-сущности (сделки, редакционный календарь, решения) и требует обучения; собственник не должен читать дашборды инженеров.

Статусы везде единые: **GREEN** норма / **YELLOW** отклонение / **RED** требуется вмешательство / **GREY** нет данных (сервис недоступен или отдел не запущен — честный сигнал, а не дыра).

## 2. Уровни

### Уровень 1 — Executive View
REVENUE, CASH, PIPELINE, SALES, CLIENTS, PRODUCT, CONTENT, DEVELOPMENT, OPERATIONS, R&D, AI COST, SECURITY STATUS. Каждый блок — один статус-индикатор + одна цифра. Клик → уровень ниже. Сверху — блок DECISIONS REQUIRED FROM ANASTASIA (максимум 5–7).

### Уровень 2 — Business Units
Личный бренд / Проявленность / Ярдники / ВФОРУМЕ / R&D. Для каждого: revenue, plan/fact, pipeline, active tasks, blocked tasks, cost, ROI, health.

### Уровень 3 — Departments
Sales, Content, Product, Development, Operations, Success, R&D, Security. KPI, tasks, errors, bottlenecks, SLA, cost, business impact.

### Уровень 4 — AI Workforce
По каждому AI worker: ONLINE/OFFLINE, текущая задача, последний результат, success rate, avg cost, avg latency, error rate, review score. Отдельный срез по провайдерам: Codex, Claude, Gemini, OpenAI, другие модели (данные из `model_runs`).

### Уровень 5 — Infrastructure
Схема: SPAIN PRIMARY / KAZAKHSTAN BACKUP / RUSSIA PRODUCTION + Git, databases, connectors, model providers. Статусы UP / DEGRADED / DOWN. Детали: CPU, RAM, disk, network, database, queue, API, backup (включая `last_successful_restore_test`), last successful deployment.

## 3. Workflow visualization

Каждый workflow run — визуальная цепочка шагов:

```
LEAD   ✓ research  ✓ qualification  ✓ offer  ● waiting reply  ○ meeting  ○ proposal  ○ payment
DEV-391  ✓ specification  ✓ Codex  ✓ Claude  ✓ tests  ✕ staging  ○ production
```

Клик по шагу: что произошло, почему ошибка, кто отвечает, что уже предпринималось (retry-история), что предлагается сделать (рекомендация orchestrator'а + кнопки действий по permissions).

## 4. Incident Center

Отдельный экран. Карточка инцидента:

```
CRITICAL  RU Production API unavailable
started: 14:32        detected by: Monitoring
affected: VFORUME
suspected cause: database connection exhaustion
automatic actions: restart attempted → failed
recommended: switch read traffic / inspect database
human required: YES
```

Собственник не ищет проблему в логах: видит суть, воздействие, что система уже попробовала, и что предлагается. Действия из карточки (approve recommended action / escalate / acknowledge).

## 5. Observability stack — выбор для MVP (§44)

Рассмотрены: Prometheus, Grafana, Loki, OpenTelemetry, Sentry, Uptime Kuma.

| Потребность | Решение | Почему |
|---|---|---|
| Метрики (server, DB, queue, app) | **Prometheus + node-exporter + postgres-exporter** | стандарт, дёшево в эксплуатации |
| Логи | **Loki + promtail** | один бинарь, интеграция с Grafana, нет Elasticsearch |
| Дашборды (инженерные) | **Grafana** | бесплатно, стандарт |
| Алерты | **Alertmanager → Telegram** | один канал, который собственник читает |
| Внешняя доступность (blackbox) | **Prometheus blackbox exporter** | вместо Uptime Kuma: одна система меньше, те же HTTP-probes |
| Traces | **отложено** (OpenTelemetry → Tempo) | на MVP 12 контейнеров; traces нужны при распределённых сбоях, которых пока нет |
| Errors/APM | **Sentry — отложено** | структурированные логи в Loki закрывают MVP; Sentry — когда появится публичный фронтенд с реальными пользователями |

**Итого: Prometheus + Grafana + Loki + Alertmanager + blackbox exporter.** Пять систем не ставим; двух (Prometheus+Grafana как связка, Loki) достаточно.

Бизнес-метрики Control Tower (workflow runs, agent runs, cost, approvals) — не из Prometheus, а напрямую из PostgreSQL: это данные, а не телеметрия. Prometheus покрывает только технические метрики.

Покрытие из ТЗ §44: application ✓ (Prometheus), server ✓ (node-exporter), database ✓ (postgres-exporter), network ✓ (node-exporter + tailscale status), workflow runs ✓ (БД), agent runs ✓ (БД), model API ✓ (метрики model-router'а), deploys ✓ (БД + события), queue ✓ (метрики orchestrator'а), security ✓ (см. SECURITY.md, Security Center), backups ✓ (restic exit codes → метрика + `restore_test_success`).

## 6. Первый показатель успеха (§47)

Founder AI OS v0.1 считается работающей, когда собственник открывает один интерфейс (Control Tower) и видит:

1. Что сейчас делает AI-компания
2. Какие задачи выполняются
3. Кто их выполняет
4. Что завершено
5. Где ошибки
6. Где задержки
7. Расходы на AI
8. Какие результаты получил бизнес
9. Есть ли security incident
10. Какие решения требуются от собственника

— и при этом редакция «Сила малых групп» реально выпускает контент через созданный workflow.

Это acceptance-критерий всей системы, зафиксирован в ROADMAP §5.


================================================================================
# ФАЙЛ: docs/GOVERNANCE.md
================================================================================

# GOVERNANCE.md — управленческий ритм и принцип управления

## 1. Принцип управления (§48)

Founder AI OS — не система, которую собственник обслуживает, а система, которая сама сообщает одно из трёх:

1. «Всё работает нормально» (зелёная сводка, раз в день, одной строкой).
2. «Возникло отклонение» (жёлтое: что, где, что уже предпринято).
3. «Требуется ваше решение» (красное/блокирующее: вопрос, варианты, рекомендация, дедлайн ответа).

Собственник управляет исключениями и направлением, не микрозадачами. Технически это означает:
- по умолчанию собственнику приходит **только дайджест отклонений**, а не поток событий;
- всё остальное доступно по запросу в Control Tower (см. CONTROL_TOWER.md);
- любое решение, требующее собственника, оформляется как approval/ decision с вариантами и рекомендацией — никогда открытым вопросом «что делаем?»;
- лимит: не более **5–7 пунктов** в блоке DECISIONS REQUIRED FROM ANASTASIA; при превышении AI CEO обязан агрегировать или пере-приоритизировать, а не передавать шум.

## 2. Weekly Executive Meeting (§41)

Обязательный ритм: раз в неделю, автоматически, по расписанию (workflow `weekly-executive-meeting`, trigger: cron, понедельник 08:00 Europe/Moscow — время настраивается).

### Участники (роли)

AI CEO (председатель), Head of Sales, Head of Product, Head of Content & Growth, AI CTO, Head of Operations, Client Success, R&D Director, Chief Decision Scientist, AI CISO. Опционально: Finance, Legal. На MVP отсутствующие отделы отчитываются статусом GREY («нет данных») — это честный сигнал, а не дыра в отчёте.

### Этап 1. Отчёты отделов (автоматически, до совещания)

Каждый отдел генерирует стандартизированный отчёт из данных системы (tasks, metrics, cost_logs — не «написанный» текст, а сводка фактов + LLM-интерпретация):

1. Цель недели
2. План
3. Факт
4. KPI
5. Что закончено
6. Что не закончено
7. Почему
8. Bottleneck
9. Новые риски
10. Новые возможности
11. План на следующую неделю
12. Решения, требуемые от AI CEO
13. Решения, требующие собственника

Пункты 7–10 — единственные «творческие»; всё остальное — запросы к БД.

### Порядок повестки — MONEY FIRST (§64)

Совещание начинается не с рассказов отделов. Фиксированный порядок:

1. CASH (13-week forecast, три сценария)
2. REVENUE / PROFIT (management P&L по business units)
3. SALES PIPELINE
4. CUSTOMER / MARKET SIGNALS
5. PRODUCT
6. MARKETING
7. DELIVERY / OPERATIONS
8. DEVELOPMENT
9. SECURITY
10. R&D
11. CAPITAL & ATTENTION ALLOCATION (Founder Attention ROI по проектам)
12. OWNER DECISIONS

Главный вопрос недели: **«Где следующий лучший рубль и следующий лучший час создадут максимальную ценность?»**

### Этап 2. Синтез AI CEO

```
DEPARTMENT REPORTS
→ CROSS-DEPARTMENT ANALYSIS   (где отделы влияют друг на друга)
→ CONFLICT DETECTION          (противоречия: продажи обещают то, чего нет в roadmap)
→ BOTTLENECK ANALYSIS         (общий узкий ресурс: reviewer, budget, approval)
→ FINANCIAL EFFECT            (стоимость недели vs эффект)
→ PRIORITIZATION              (пересборка приоритетов)
→ EXECUTIVE AGENDA
```

### Этап 3. Законченный продукт: WEEKLY EXECUTIVE DECISION PACK

Единый документ (сохраняется в `documents`, версия в `decisions`): состояние бизнеса, отклонения, деньги, pipeline, продукт, разработка, контент, операции, клиенты, R&D, безопасность, критические зависимости, решения, **задачи на неделю с владельцами и дедлайнами**.

Отдельный блок: **DECISIONS REQUIRED FROM ANASTASIA** — максимум 5–7 пунктов, каждый: вопрос → варианты → tradeoffs → рекомендация → что произойдёт по умолчанию, если ответа нет к дедлайну.

### Этап 4. Решения становятся задачами

Никаких решений, оставшихся в тексте протокола. Каждое решение из пакета:

```
DECISION → OWNER → TASK (task.schema.json) → DEADLINE → KPI → CONTROL (проверка на следующем совещании)
```

Оркестратор создаёт задачи автоматически; решения из блока собственника создают задачи только после её ответа (или применяется «что произойдёт по умолчанию» после дедлайна — явно зафиксированное в пакете).

### Контроль

На следующем совещании первый раздел пакета — отчёт по задачам прошлого пакета: done / not done / why. Задача из decision pack не может «потеряться»: она либо completed, либо escalated.

## 3. Ежедневный ритм

- 09:00 — зелёная/жёлтая сводка в Telegram (1–5 строк): статусы контуров, инциденты за ночь, расход AI за вчера, pending approvals.
- Мгновенные алерты — только CRITICAL (security, production down, budget breach).
- Всё остальное ждёт дайджеста. Настройка «тихих часов» — в policies.


================================================================================
# ФАЙЛ: docs/FINANCE.md
================================================================================

# FINANCE.md — Financial Decision System

## 1. Главный принцип (§49)

Компания производит деньги, а не задачи. Система НЕ оптимизируется по количеству выполненных задач. Целевые метрики всей системы:

**REVENUE · GROSS PROFIT · CONTRIBUTION MARGIN · CASH · CUSTOMER VALUE · RETENTION · CAPITAL EFFICIENCY · FOUNDER ATTENTION EFFICIENCY**

Каждый отдел знает свой финансовый вклад. Каждый крупный проект имеет карточку экономики (`project_economics`): revenue potential, direct cost, AI cost, human hours, founder hours, expected margin, actual margin, payback, strategic value, probability of success.

## 2. Законченный продукт отдела

Не таблица расходов, а **Financial Decision System**, которая ежедневно/еженедельно отвечает на 11 вопросов:

1. Сколько у нас денег? 2. Откуда пришли? 3. На чём зарабатываем? 4. Где теряем? 5. Где растут расходы? 6. Какие продукты маржинальнее? 7. Какие клиенты прибыльные? 8. Какие проекты съедают время собственника? 9. Какие агенты/модели стоят слишком дорого? 10. Что остановить? 11. Куда выгоднее следующий рубль и следующий час?

Ответы — материализованные представления (SQL views) поверх таблиц + LLM-интерпретация в weekly pack. Вопросы 1–9 — детерминированные запросы, не LLM.

## 3. Роли → агенты (функции, не модели)

| Агент | Роли | Фаза |
|---|---|---|
| `ai-cfo` | CFO + FP&A + Investment Analyst | P2 (finance-lite), полный P5 |
| `management-accountant` | Management Accountant + Cost Controller | P5 |
| `unit-economics-analyst` | Unit Economics Analyst | P5 |
| `cash-controller` | Cash & Treasury Controller | P2 (13-недельный forecast) |
| `time-attention-analyst` | Time & Attention Analyst | P5 |
| `financial-auditor` | Financial Auditor (входит в Risk/Audit Council) | P5 |

На MVP роли CFO выполняет расширенный AI CEO + детерминированные отчёты; выделенный `ai-cfo` появляется, когда транзакций достаточно для полноценного FP&A.

## 4. Management P&L (§51)

Отдельный P&L по каждому business unit (Я / Проявленность / Ярдники / ВФОРУМЕ / R&D), строки: Revenue, COGS, AI Costs, Contractors, Human Labour, Marketing, Sales, Infrastructure → Gross Profit → Contribution Margin → Operating Profit. По каждой строке: план / факт / forecast.

Источник данных: `financial_transactions` (единая классификация, см. DATABASE.md §A) + `cost_logs` (AI costs пишутся автоматически из model_runs — это единственная полностью автоматическая строка на старте). Остальные строки на MVP — еженедельный импорт (csv/ручной ввод через форму), пока нет банковских интеграций. Честное ограничение: без интеграции с банком P&L на 80% ручной — это принято, автоматизация банковских фидов отложена.

## 5. 13-Week Cash Flow (§52)

Rolling forecast, 13 недель, еженедельный пересчёт (workflow, часть weekly meeting):

Строки: opening cash → confirmed inflows → probable inflows (взвешенные по probability из deals) → fixed costs → variable costs → payroll → taxes → AI/API (из cost_logs) → servers → marketing → contractors → investments → closing cash.

Три сценария: BASE / NEGATIVE / UPSIDE. Правило алерта: если в NEGATIVE closing cash любой недели < 1,5 × ежемесячных fixed costs → YELLOW; < 1,0 → RED + alert немедленно, не дожидаясь совещания.

## 6. Time & Attention Ledger (§53)

Таблица `time_entries`: кто (founder / top_manager / human / ai_run), по какому проекту, сколько часов, источник. Учёт времени собственника — обязателен; учёт остальных — по мере появления.

Как собирается на MVP без слежки: approvals, owner_decisions и owner_review в системе имеют timestamps — founder hours по ним считаются автоматически; остальное — 2-минутный еженедельный опрос в Telegram («чем занималась по проектам на этой неделе», кнопки + часы). Никаких трекеров — доверие важнее точности.

Главная метрика: **FOUNDER ATTENTION ROI = Contribution Margin / Founder Hours**.

Вывод системы (автоматически, в weekly pack):
```
Проект A: 12 ч внимания собственника → CM 900 000 ₽  (75 000 ₽/час)
Проект B: 41 ч → CM 180 000 ₽                        ( 4 390 ₽/час)
→ Вопрос: «Почему мы продолжаем B?» + recommendation (STOP/REDESIGN/DELEGATE)
```
Opportunity cost считается против лучшей альтернативы портфеля.

## 7. Unit Economics Engine (§54)

Автоматический расчёт (SQL + агрегации): CAC, LTV, LTV/CAC, CAC payback, ARPU, gross margin, contribution margin, retention, churn, expansion revenue, revenue per customer, **revenue per founder hour**, revenue per employee, **AI cost per outcome**.

Для сервисных продуктов (ретриты, группы, обучение): project margin, client margin, hours per delivery, margin per delivery hour.

На MVP реально вычислимы: CAC (при атрибуции контент→lead→deal), gross/contribution margin, AI cost per outcome, revenue per founder hour. LTV/retention требуют истории повторных продаж — честно помечаются «недостаточно данных» вместо выдуманных цифр.

## 8. Financial Kill Rules (§55)

У каждого проекта в `project_economics.kill_criteria` — машинно-проверяемые условия:

- после X тестов нет willingness to pay;
- CAC > допустимого порога;
- gross margin < порога;
- founder hours > порога на единицу результата;
- acquisition не масштабируется;
- infrastructure/API costs съедают economics;
- прогноз payback > допустимого горизонта.

Проверка — еженедельно (детерминированный код). Срабатывание → система обязана выдать рекомендацию одним из шести действий: **STOP / REDESIGN / RAISE PRICE / AUTOMATE / DELEGATE / SCALE** — с расчётом. Решение принимает собственник (decision в weekly pack).

## 9. Связь с остальной системой

- AI Costs: model_runs → cost_logs → P&L строка «AI Costs» — автоматически, по tenant/BU/project.
- Founder hours: approvals + weekly опрос → time_entries → FOUNDER ATTENTION ROI — в Control Tower, уровень 1.
- Kill rules срабатывания → инциденты типа `financial` → weekly pack + отдельный alert при RED.
- Cash flow риск → блок DECISIONS REQUIRED FROM ANASTASIA с готовыми опциями.


================================================================================
# ФАЙЛ: docs/REVENUE_SYSTEM.md
================================================================================

# REVENUE_SYSTEM.md — от customer insight до денег

Центральный цикл компании (§71) — всё остальное ему обслуживает:

```
CUSTOMER → RESEARCH → INSIGHT → PRODUCT MEANING → POSITIONING
→ MARKETING → QUALIFIED DEMAND → SALES → MONEY → DELIVERY
→ CUSTOMER RESULT → RETENTION → MORE REVENUE → DATA
→ FINANCE / PRODUCT / R&D ↺
```

## 1. Customer & Market Intelligence (§56–57)

Функция существует ДО Marketing и Sales. Запрещённый вопрос: «как продать наш продукт?» — пока не доказано: КОМУ, КАКУЮ ПРОБЛЕМУ, НАСКОЛЬКО БОЛЬНО, КАК РЕШАЮТ СЕЙЧАС, ПОЧЕМУ ЭТОГО НЕДОСТАТОЧНО, СКОЛЬКО ГОТОВЫ ПЛАТИТЬ, КТО ПРИНИМАЕТ РЕШЕНИЕ, ЧТО МЕШАЕТ ПОКУПКЕ.

Источники: интервью, звонки продаж, переписки, анкеты, причины отказов, поведение пользователей, support, отзывы, поисковые запросы, конкуренты, публичные обсуждения.

Каждый insight — запись в `customer_insights` с обязательными полями: SOURCE, SEGMENT, PROBLEM, FREQUENCY, SEVERITY, CURRENT_SOLUTION, WILLINGNESS_TO_PAY, EVIDENCE_LEVEL. **Мнение одного клиента ≠ рынок**: `evidence_level` (single_case / few_cases / pattern) и приоритизация только при pattern.

Роли → агенты (P3–P5): `head-of-customer-intelligence` (Head + Insight Synthesizer), `market-researcher` (Market + Competitor + Pricing), `customer-researcher` (Customer Research + JTBD + Behaviour).

## 2. Product Meaning & Positioning (§58)

Роль Head of Positioning / Value Architect. Для каждого продукта — карточка `positioning`: ICP, JTBD, CORE PROBLEM, PROMISE, PROOF, DIFFERENTIATION, ALTERNATIVES, REASONS TO BELIEVE, VALUE METRIC, PRICE LOGIC.

Восемь вопросов, на которые карточка обязана отвечать: что продаём на самом деле; почему покупателю важно; почему сейчас; почему мы; с чем сравнивают; почему конкурент хуже/лучше; какую категорию создаём или занимаем; что покупатель скажет о нас одним предложением.

Без заполненной карточки продукт не получает marketing-задач. Это gate, а не рекомендация.

## 3. Marketing (§59)

Marketing не производит контент. **Marketing производит QUALIFIED DEMAND.** Контент — инструмент (и живёт в редакции, см. EDITORIAL.md). Законченный продукт отдела: QUALIFIED LEADS, MEETINGS, PIPELINE, REVENUE — не охваты и не посты. Обязательна связка attribution с CRM: каждый lead несёт источник (content_item_id / канал / кампания).

Роли (P3+): CMO, Head of Growth, Positioning Strategist, Demand Generation, Brand Director, Content & Editorial (уже есть в редакции), Performance Analyst, Partnerships, Marketing Analyst. На MVP это 1–2 агента: `growth-demand` + аналитика внутри него.

## 4. Sales (§60) и Value Selling (§61)

Sales — revenue department. Система продаж:

```
ICP → account research → trigger → contact → discovery → problem
→ economic value → proposal → objections → negotiation → contract
→ payment → expansion
```

**Value selling — обязательный расчёт перед предложением** (заполняется в `deals.value_hypothesis`):

| Поле | Вопрос |
|---|---|
| current_cost_of_problem | сколько проблема стоит клиенту сейчас (деньги) |
| lost_revenue | что клиент теряет, не решая |
| human_hours | сколько часов уходит |
| risk | цена риска |
| expected_value | ожидаемый эффект решения |
| payback | срок окупаемости для клиента |

Форма предложения: не «AI-платформа стоит 300 000», а «сейчас этот процесс стоит компании X млн / Y часов; после внедрения — Z; экономический эффект — N». Предложение без заполненной value hypothesis не уходит клиенту — workflow блокируется.

## 5. Revenue Operations (§62)

Единый RevOps layer: MARKETING + SALES + CLIENT SUCCESS + FINANCE. **Один customer ID, одна CRM, одна история**: first touch → content → lead → meeting → offer → payment → delivery → renewal → upsell.

Технически уже заложено в ER-модели: `customers` — единственный источник правды о клиенте; `leads.content_item_id` — атрибуция маркетинга; `deals` — деньги; `content_items` ↔ `leads` ↔ `deals` образуют цепочку без дублей. Запрещено заводить параллельные таблицы клиентов в отделах — нарушение считается архитектурным дефектом на review.

## 6. Топ-команда (§63)

Каждая роль имеет «главный продукт» — законченный результат, по которому её судят:

| Роль | Главный продукт | Ключевые KPI |
|---|---|---|
| AI CEO / GM | достижение целей компании | revenue, profit, cash, return on resources |
| CFO | финансово устойчивый прибыльный бизнес | cash runway, margin, forecast accuracy |
| CRO / Revenue Director | предсказуемая выручка | pipeline coverage, win rate, forecast accuracy |
| CMO | предсказуемый поток квалифицированного спроса | qualified leads, CAC, pipeline from marketing |
| CPO | продукт, за который платят и продолжают платить | retention, activation, WTP evidence |
| CTO | работающая система, быстро создающая ценность | release success rate, time to production, AI cost |
| COO | предсказуемое исполнение | SLA, blocked tasks, cycle time |
| CISO | управляемый уровень риска | incidents, unresolved findings, alert latency |
| Chief Decision Scientist | решения на вероятностях и данных | калибровка прогнозов, decision quality |
| Chief of Staff / Orchestrator | ни одно решение не теряется между отделами | decision follow-through rate |

На MVP один агент может держать несколько ролей (AI CEO + Chief of Staff — один агент `ai-ceo` + `operations-controller`), но «главный продукт» роли не размывается: KPI считается по роли, а не по агенту.

## 7. Money-first порядок совещания (§64)

См. GOVERNANCE.md §2 — порядок повестки изменён: CASH → REVENUE/PROFIT → PIPELINE → CUSTOMER SIGNALS → PRODUCT → MARKETING → DELIVERY → DEVELOPMENT → SECURITY → R&D → CAPITAL & ATTENTION ALLOCATION → OWNER DECISIONS. Главный вопрос недели: **«Где следующий лучший рубль и следующий лучший час создадут максимальную ценность?»**


================================================================================
# ФАЙЛ: docs/COUNCILS.md
================================================================================

# COUNCILS.md — четыре совета компании

## 1. Зачем четыре, а не один

| Совет | Вопрос | Когда |
|---|---|---|
| **Executive Council** | Что делать сейчас? | еженедельно (weekly meeting) |
| **Entrepreneurial Council** | Где деньги и масштаб? | большие решения: бизнес-модель, цены, инвестиции, новый продукт, закрытие, масштабирование |
| **Creative Council** | Что ещё возможно? | важные продуктовые/стратегические задачи, до оценки реалистичности |
| **Risk / Audit Council** | Почему это может провалиться? | перед крупным решением |

**Правило разделения:** советы не смешиваются в одном запуске. Иначе творческая идея будет убита финансистом на первой минуте — или безумная идея уйдёт в производство без проверки. Creative расширяет пространство, Risk сужает, Entrepreneurial оценивает деньги, Executive решает.

## 2. Принцип честности (жёсткий)

Advisory lenses построены **только** на публичных источниках: книги, интервью, акционерные письма, выступления, проверяемые кейсы.

Система НИКОГДА:
- не утверждает, что реальные люди участвуют в компании;
- не имитирует их личности, голос, стиль;
- не придумывает их мнение по вопросу, которого нет в источниках.

Система ДЕЛАЕТ: применяет документированный паттерн мышления («оптику») к нашему fact pack и явно показывает, на каких публичных принципах основан каждый тезис. Каталог оптик: [blueprints/councils.yaml](../blueprints/councils.yaml). Формат вывода lens: «Оптика X (принципы: …) задаёт вопрос: … Применительно к нашему случаю это означает проверку: …».

## 3. Процесс Entrepreneurial Council

Совет НЕ собирается на каждую задачу — только для: новой бизнес-модели, ценообразования, больших инвестиций, нового продукта, крупной смены стратегии, закрытия проекта, масштабирования.

```
DECISION
→ FACT PACK          (что мы знаем: цифры, constraints)
→ FINANCIAL MODEL    (из FINANCE.md: margins, payback, сценарии)
→ CUSTOMER EVIDENCE  (из customer_insights: frequency, severity, WTP)
→ 3–5 RELEVANT LENSES (не все 12 — только релевантные типу решения)
→ CRITIQUE           (каждая оптика критикует варианты)
→ CONTRADICTIONS     (где оптики противоречат — это самое ценное)
→ DECISION OPTIONS
```

Итог — не голосование. AI CEO формирует: OPTION A / B / C, EXPECTED VALUE, RISKS, REVERSIBILITY, RECOMMENDATION, EVIDENCE. Решение принимает собственник; всё фиксируется в `decisions` с полем «what evidence would change this decision».

## 4. Процесс Creative Council

1. Первые 20% процесса текущие ограничения не обсуждаются.
2. Минимум 10 существенно различных направлений (не вариации одной идеи).
3. Аналогии из других индустрий (cross-industry-analogy-agent).
4. Стресс-вопросы: без существующей бизнес-модели? / в 10 раз дешевле? / в 10 раз дороже? / без людей? / без интерфейса? / клиент платит только за результат? / стартовый капитал почти ноль?

После divergence обязательная convergence-цепочка: **Product Council → Finance → Customer Research → Technical Feasibility → TEST**. Creative Council не имеет права утверждать инвестиции — его продукт: расширенное пространство вариантов с быстрым тестом для лучших.

## 5. Risk / Audit Council

Состав: AI CISO + Reviewer/Auditor + Financial Auditor. Вход: решение до исполнения. Выход: риски по severity, kill criteria, и обязательный пункт — «что должно оказаться правдой, чтобы это решение провалилось» (inversion). Проваливается в weekly pack или в approval payload для high-risk действий.

## 6. Связь с Decision Science layer

Все четыре совета пишут в `decisions` (см. DATABASE.md): question, options, assumptions, probabilities, expected value, chosen, evidence_that_changes. Это позволяет через квартал оценивать калибровку советов: сколько рекомендаций Entrepreneurial Council оказались верными по факту. Совет без обратной связи по результатам — театр.


================================================================================
# ФАЙЛ: docs/DEPLOYMENT.md
================================================================================

# DEPLOYMENT.md

## 1. Deployment flow (техническая реализация)

```
Task → AI CTO (mode) → worktree(s) → Codex/Claude → report.json + patch
→ cross-review → MR → CI: lint → typecheck → unit → integration → build image :<sha>
→ push registry → deploy staging (авто) → e2e/browser tests на staging
→ security review (если scope требует) → human approval (если high-risk)
→ deploy-broker → RU production → healthcheck (30s, 3 probes)
→ OK → task completed | FAIL → автоматический rollback на предыдущий tag → incident
```

Реализация по шагам:
- **CI**: GitHub Actions (или self-hosted runner на Spain, если код не должен покидать периметр — для MVP допустим GitHub private repo, секреты CI ограничены staging).
- **Registry**: GHCR (MVP) → свой registry на Spain позже.
- **Staging deploy**: webhook от CI → orchestrator → deploy локально на Spain compose-проект `staging`.
- **Production deploy**: только через deploy-broker (см. SECURITY.md §6). High-risk (миграции с DDL, auth, payments) — approval обязателен, иначе деплой блокируется политикой.
- **Rollback**: каждый deploy хранит `previous_image_tag`; rollback = одна команда брокера, ≤ 2 минут. DB-миграции — forward-only совместимые (expand/migrate/contract), деструктивные изменения — отдельной миграцией после стабилизации.

## 2. Порядок установки на серверы (первый раз)

### Шаг 0 — подготовка (локально, 1 час)
1. Завести: Tailscale account, GitHub org, 3 VPS, object storage (off-provider), Telegram bot (через @BotFather), API-ключи OpenAI/Anthropic/Google.
2. Сгенерировать age-ключи (spain, kazakhstan, russia), мастер-ключ владельца — офлайн.
3. Склонировать `infrastructure` repo, заполнить `.env` из `.env.example`, зашифровать через SOPS.

### Шаг 1 — Spain (2–3 часа)
```bash
ssh root@<spain-ip>
curl -sSL https://<git>/infrastructure/bootstrap/install-spain.sh | bash
```
Скрипт: hardening SSH → создаёт пользователей → ставит Docker, Node, Python, CLI → tailscale up (auth key) → клонирует репозитории → sops -d secrets → docker compose up -d → миграции БД → регистрация в monitoring.
Проверка: `curl https://api.<domain>/health`, Grafana открывается, тестовая задача проходит очередь.

### Шаг 2 — Russia (1–2 часа)
```bash
curl -sSL https://<git>/infrastructure/bootstrap/install-russia.sh | bash
```
Отличия: нет LLM-ключей, нет agent-runner; ставится reverse proxy, deploy-broker-exec, production compose для ВФОРУМЕ, node-exporter, restic-клиент.
Проверка: из Spain `ssh deploy-ai@ru-node deploy vforume <tag>` — деплой проходит, healthcheck зелёный.

### Шаг 3 — Kazakhstan (1 час)
```bash
curl -sSL https://<git>/infrastructure/bootstrap/install-kazakhstan.sh | bash
```
Ставит: docker, restic-клиент, git-mirror cron (pull всех репо каждые 15 мин), restore-скрипты, SOPS-ключ kazakhstan. Никаких запущенных prod-сервисов.
Проверка: тестовый restore PostgreSQL из последнего бэкапа в контейнере.

### Шаг 4 — smoke-тест end-to-end
Запустить MVP-задачу №1 (см. ROADMAP.md §2). Полный цикл до production.

## 3. Список необходимых credentials/access

| # | Что | Где хранится | Кто/что использует |
|---|---|---|---|
| 1 | OpenAI API key | SOPS spain | model-router |
| 2 | Anthropic API key | SOPS spain | model-router |
| 3 | Google AI API key | SOPS spain | model-router |
| 4 | Tailscale auth keys (per node, tagged, reusable=false) | SOPS per-node | install-скрипты |
| 5 | GitHub: deploy key (read) + PAT для CI | SOPS spain / GitHub Secrets | agent-runner, CI |
| 6 | SSH ключ deploy-ai (пара) | приватный — SOPS spain; публичный — authorized_keys на RU | deploy-broker |
| 7 | PostgreSQL superuser + app user + migrator | SOPS spain | orchestrator, миграции |
| 8 | Telegram bot token + chat_id владельца | SOPS spain | orchestrator (alerts, approvals) |
| 9 | Object storage keys (restic repo) | SOPS per-node | restic |
| 10 | restic encryption password | офлайн мастер-ключ + SOPS | restore |
| 11 | Google service account (Drive/Gmail/Calendar connectors) | SOPS spain | connectors |
| 12 | Домен + DNS API token (для Caddy TLS) | SOPS per-node | caddy |
| 13 | SOPS age private keys ×3 | на узлах /root/.config/sops + мастер офлайн | sops |
| 14 | HMAC secret для approval callbacks | SOPS spain | orchestrator |

## 4. Операционные регламенты

- Обновление образов ОС и docker — раз в 2 недели, сначала KZ (он пустой), потом RU, потом Spain в окне.
- Любое ручное изменение на сервере запрещено — только через install-скрипты/compose в Git. Обнаруженный drift устраняется переприменением конфигурации.
- Доступ владельца: ноутбук в tailnet (tag:admin), SSH через `ops`.


================================================================================
# ФАЙЛ: docs/DISASTER_RECOVERY.md
================================================================================

# DISASTER_RECOVERY.md

## 1. Принципы

- Система не зависит от одного хостинг-провайдера и от одной страны.
- Бэкап, который не восстанавливали, — не бэкап. Restore test — регулярная процедура, а не надежда.
- Все бэкапы шифруются клиентски (restic) до отправки в storage.

## 2. Что и куда бэкапится

| Данные | Метод | Частота | Куда |
|---|---|---|---|
| PostgreSQL control-plane (Spain) | WAL-архив + nightly base (pg_dump через restic stdin) | WAL continuous, base nightly 03:17 UTC | Object storage (off-provider) + pull-копия на KZ |
| PostgreSQL production (RU) | WAL + nightly base | то же | RU object storage (RU-юрисдикция) + владелец решает о выходе за пределы РФ отдельно |
| Git | push в 2 remotes (GitHub + зеркало на KZ) | каждый push / 15 мин зеркало | GitHub + KZ |
| Docker images | registry retention + weekly export ключевых образов | weekly | registry + KZ |
| Секреты | SOPS-файлы в Git + мастер-ключ офлайн | при изменении | Git + офлайн носитель |
| Конфигурация (compose, env шаблоны, ACL) | Git | при изменении | GitHub + KZ |
| Audit logs export | daily export, WORM bucket | daily | object storage с object lock |
| Knowledge/documents | источники (GDrive) — provider-native; чанки пересобираются | ingestion повторяем | — |

## 3. RPO / RTO

| Система | RPO | RTO | Механизм |
|---|---|---|---|
| Founder AI OS control-plane | ≤ 15 мин (WAL) | ≤ 4 ч | активация KZ warm standby |
| ВФОРУМЕ production (RU) | ≤ 15 мин | ≤ 1 ч | restore на том же или запасном RU VPS |
| Git | ~0 (два remote) | ≤ 30 мин | переключение remote |
| Документы (GDrive) | provider SLA | provider SLA | экспорт критичных документов weekly в object storage |
| Secrets | последняя версия в Git | ≤ 1 ч | мастер-ключ + sops |

## 4. Процедура: полная потеря Spain-node

Предусловия: KZ-node жив, в tailnet, имеет свежие зеркала и бэкапы.

1. **Объявить инцидент**, зафиксировать время последней WAL в бэкапе (это граница потерь).
2. На KZ: `restore-control-plane.sh --latest` — restic restore → PostgreSQL base + WAL replay до последней точки.
3. Применить SOPS-ключ kazakhstan к зашифрованным секретам (LLM-ключи дублированы в sops-файле для KZ-контура).
4. `docker compose -f docker-compose.kz.yml up -d` — профиль standby→active (orchestrator, model-router, agent-runner, n8n, monitoring).
5. Обновить DNS `api.<domain>` → KZ IP (TTL заранее 300s) — human approval, т.к. DNS в списке критичных.
6. Проверить: health endpoints, тестовая задача через очередь, связность с RU (deploy-broker на KZ имеет свой ключ deploy-ai — второй authorized key на RU).
7. Объявить Spain потерянным; при появлении нового Spain-сервера — install-spain.sh, репликация в обратную сторону, возврат primary по плану.

Ожидаемое время при отработанной процедуре: 2–4 часа. Первый реальный прогон — обязательный учебный (см. §5).

**Что НЕ восстанавливается на KZ:** staging-окружение (можно пожертвовать), очередь задач в статусе `running` (помечаются `failed` с reason=node_loss, перезапускаются по retry policy).

## 5. Restore testing

- **Ежемесячно, 1-е число:** автоматический restore PostgreSQL nightly backup в изолированный контейнер на KZ + прогон стандартных SQL-проверок (количество строк в ключевых таблицах, целостность hash-chain аудита). Результат — запись в `audit_logs` и метрика `restore_test_success`.
- **Ежеквартально:** полный учебный DR-прогон §4 с секундомером. Отчёт владельцу: фактический RTO, что сломалось, что поправить.
- Отсутствие успешного restore test > 45 дней → автоматический инцидент HIGH.

## 6. Потеря других узлов

- **RU-node:** сайты падают → развёртывание на запасном RU VPS по install-russia.sh + restore production DB (RTO ≤ 1 ч). Founder AI OS продолжает работать — это отдельный контур, и это правильно.
- **KZ-node:** некритично. Поднять новый за 1 час, восстановить зеркала. Риск-окно: до восстановления KZ нет standby.
- **Два узла одновременно:** GitHub + object storage вне периметра — восстановление с нуля по install-скриптам, RTO ~1 рабочий день. Мастер-ключ офлайн — критично, без него секреты не восстановить.


================================================================================
# ФАЙЛ: docs/ROADMAP.md
================================================================================

# ROADMAP.md

## 1. Принцип реализации

ARCHITECTURE → REVIEW → MVP PLAN → FOUNDATION → ONE END-TO-END WORKFLOW → только потом масштабирование. Не строим 50 агентов, Kubernetes, Temporal, microservices everywhere. PostgreSQL + Redis + Docker + n8n + backend достаточно.

## 2. MVP — точный состав (обновлено по Дополнению к ТЗ §46)

**Порядок приоритетов изменён: первым бизнес-процессом становится редакция «Сила малых групп» (P1), а не Sales.**

- **P0 — FOUNDATION:** infrastructure, PostgreSQL, Task Protocol, Orchestrator, Agent Registry, Audit Log, Permissions, Security baseline, Observability baseline.
- **P1 — РЕДАКЦИЯ «СИЛА МАЛЫХ ГРУПП»:** полноценная AI-редакция (см. EDITORIAL.md). Первый end-to-end бизнес-тест: SOURCE → AI EDITORIAL SYSTEM → REVIEW → OWNER APPROVAL → PUBLISHED CONTENT → ANALYTICS.
- **P2 — CONTROL TOWER:** собственник визуально видит редакцию, инфраструктуру и AI workers (см. CONTROL_TOWER.md).
- **P3 — SALES:** замыкание коммерческой петли CONTENT → CTA → LEAD → CRM → SALES (workflow mvp2-lead-to-deal).
- **P4 — DEVELOPMENT DUO:** Codex + Claude для развития самой Founder AI OS и ВФОРУМЕ (workflow mvp1-code-to-production).
- **P5 — PRODUCT / OPERATIONS / SUCCESS.**
- **P6 — R&D / STARTUP LAB.**

Следствие P1: минимальный knowledge/ingestion-контур (Google Drive connector, загрузка транскриптов, обезличивание, теговый поиск) поднимается раньше полного knowledge layer с embeddings. Embeddings/pgvector — когда тегового поиска перестанет хватать.

MVP-1 по кодовому контуру остаётся как технический тест P4:
> Задача «добавить маленькую функцию во ВФОРУМЕ» → AI CTO → Codex/Claude в worktrees → cross-review → CI → staging → audit → approval → RU production → healthcheck.

### Компоненты MVP (полный список — ничего сверх этого не строим)

| # | Компонент | Фаза |
|---|---|---|
| 1 | PostgreSQL с RLS, ядро таблиц (tenants, users, roles, business_units, departments, projects, tasks, task_runs, agents, models, model_runs, approvals, audit_logs, cost_logs, content_items, documents, knowledge_items, deployments) | P0 |
| 2 | Orchestrator API: CRUD задач, статусная машина, SKIP LOCKED worker, approvals, audit writer | P0 |
| 3 | Model Router: OpenAI + Anthropic + Gemini, privacy-фильтр, cost metering, fallback | P0 |
| 4 | Security baseline: SOPS, Tailscale, gitleaks, budget guards, sandbox agent-runner | P0 |
| 5 | Observability baseline: Prometheus + Grafana + Loki + Alertmanager → Telegram + blackbox | P0 |
| 6 | Google Drive connector + ingestion + обезличивание + classification | P1 |
| 7 | 7 агентов редакции + editorial-pipeline workflow + редакционный календарь | P1 |
| 8 | Telegram-канал публикации по owner approval + карточка результата | P1 |
| 9 | Control Tower: уровни 1–5, workflow visualization, Incident Center | P2 |
| 10 | Weekly Executive Meeting workflow + Decision Pack | P2 |
| 11 | AI CISO + Security Center + weekly security report | P2 |
| 12 | CRM-таблицы (leads, deals), sales-агенты, mvp2 workflow | P3 |
| 13 | Agent-runner (Codex/Claude в worktrees) + deploy-broker + install-скрипты | P4 |

**Не входит:** полный pgvector knowledge layer, Temporal, Headscale, product/R&D-отделы, arena-аналитика (model_runs пишется с первого дня), auto-публикация без approval, multi-tenant onboarding UI.

## 3. Roadmap

| Фаза | Срок | Содержание | Критерий выхода |
|---|---|---|---|
| P0. Foundation | Нед. 1–2 | Сервера, сеть, БД, Task Protocol, orchestrator, router, security/observability baseline, install-скрипты | Orchestrator /health на всех узлах, restore test зелёный, тестовая задача проходит очередь с аудитом |
| P1. Редакция | Нед. 3–6 | Ingestion, обезличивание, 7 агентов, конвейер, календарь, owner approval, публикация | 3 материала/неделю проходят полный конвейер; минимум 1 публикация с реальным CTA |
| P2. Control Tower + Governance + Finance-lite | Нед. 7–9 | Control Tower 5 уровней, Incident Center, weekly meeting workflow (money-first), AI CISO, financial_transactions + 13-week cash flow + time_entries (опрос собственника) | Первый показатель успеха §47: 10 вопросов из одного экрана + редакция работает; CASH-блок показывает реальные цифры |
| P3. Sales + Customer Intelligence | Нед. 10–11 | CRM, sales-агенты, атрибуция контент→lead, customer_insights, карточки positioning как gate для marketing-задач | 5 реальных лидов прошли воронку до результата |
| P4. Development duo | Нед. 12–14 | Codex/Claude 4 режима, deploy-broker, MVP-1 code-to-production | MVP-1 пройден; 10 production-задач без ручного кода |
| P5. Product/Ops/Success + Finance полный + Councils | Нед. 15–18 | Отделы по blueprints; ai-cfo, unit economics engine, kill rules; формализация четырёх советов (councils.yaml) | Каждый отдел имеет workflow с измеримым бизнес-результатом; kill rule сработал на реальном проекте хотя бы раз (сигнал, что система умеет останавливать) |
| P6. R&D + hardening → продукт | Нед. 19+ | Startup Lab воронка, Headscale, dedicated-DB option, onboarding tenant | Новый tenant из blueprint без правок ядра |

Сроки — оценка при загрузке «владелец + AI-агенты», без найма. Kill-criteria: если P1 за 4 недели (нед. 3–6) не выпускает контент стабильно — стоп, разбор, а не наращивание функций.

## 4. Security checklist

- [ ] SSH: только ключи, root login off, все узлы только в tailnet
- [ ] gitleaks в pre-commit и CI зелёный
- [ ] Все секреты через SOPS; `.env` в .gitignore; репозиторий сканирован на историю утечек
- [ ] PostgreSQL: app user без SUPERUSER; RLS включён и проверен тестом «tenant A не видит tenant B» (тест в CI)
- [ ] RLS-политики на knowledge_chunks по acl_tags проверены тестом
- [ ] deploy-ai: forced command, whitelisted команды, логирование
- [ ] agent-runner: no privileged, read-only rootfs, egress allowlist, drop capabilities
- [ ] Approval: подпись callback проверяется, replay невозможен, expiry работает
- [ ] Budget guards: дневной лимит, алерт 80%, блокировка 100% — проверены тестовым превышением
- [ ] Audit: hash-chain проверяется weekly job'ом; append-only enforced на уровне БД
- [ ] Бэкапы: restic restore test прошёл; ключи шифрования офлайн
- [ ] n8n не имеет прямого доступа к PostgreSQL
- [ ] Rate limits на orchestrator API и model router
- [ ] Миграции: каждая имеет downgrade; деструктивные — только через approval

## 5. Acceptance checklist (приёмка v0.1 — по §47 дополнения к ТЗ)

**Главный критерий (§47):** собственник открывает один интерфейс (Control Tower) и видит:
- [ ] 1. Что сейчас делает AI-компания
- [ ] 2. Какие задачи выполняются
- [ ] 3. Кто их выполняет
- [ ] 4. Что завершено
- [ ] 5. Где возникли ошибки
- [ ] 6. Где возникли задержки
- [ ] 7. Какие расходы на AI
- [ ] 8. Какие результаты получил бизнес
- [ ] 9. Есть ли security incident
- [ ] 10. Какие решения требуются от собственника
- [ ] И редакция «Сила малых групп» реально выпускает контент через workflow editorial-pipeline

Технические критерии:
- [ ] Editorial pipeline: источник → обезличивание → draft → voice → critic → confidentiality → owner approval → публикация → карточка результата с leads
- [ ] Confidentiality-reviewer заблокировал тестовый материал с идентифицируемым фрагментом (проверка veto)
- [ ] Weekly Executive Meeting: decision pack собран автоматически, каждое решение стало задачей с владельцем и дедлайном
- [ ] Каждый LLM-вызов виден в model_runs с cost; дневной отчёт стоимости в Telegram
- [ ] Approval сработал через Telegram, подпись проверена, replay невозможен
- [ ] Critical security event → алерт немедленно (не ждёт weekly report)
- [ ] DR: учебный прогон «потеря Spain» ≤ 4 ч до работающего control-plane на KZ
- [ ] Независимая проверка: другой ИИ (чистый контекст) по этому пакету документов смог поднять staging без вопросов

Критерии P4 (кодовый контур, позже):
- [ ] MVP-1 выполнен от задачи до healthcheck на production без ручного кода человеком
- [ ] Cross-review зафиксирован, findings привели к rework-циклу хотя бы раз
- [ ] Rollback протестирован намеренно сломанным релизом
- [ ] P3: lead прошёл воронку до зафиксированного результата (сделка/отказ с reason)

## 6. Cost estimate MVP (цены проверены 2026-11-05)

### Инфраструктура (месяц)

| Статья | Сумма |
|---|---|
| Spain VPS (4vCPU/16GB, EU) | €20–30 |
| Kazakhstan VPS (2vCPU/4GB) | $10–15 |
| Russia VPS (2vCPU/4GB) | ₽1000–2000 (~$12–25) |
| Object storage 100–200 GB + WORM bucket | $2–5 |
| Домены, прочее | $3 |
| **Итого инфраструктура** | **~$50–80/мес** |

### AI API (месяц, при MVP-нагрузке)

Допущения: ~30 задач/день; средняя coding-задача — 150К входных + 30К выходных токенов на исполнителя, REVIEW добавляет ~60%; классификация/routing — cheap-модели; доля задач на mid-классе (Sonnet 5.5 / GPT-6.1 Sol @ $2/$10) — 80%, strong-класс (Opus 5.5 / GPT-5.6 Sol @ $4/$20) — 15%, frontier ($10/$50) — 5%.

| Класс задач | Объём | Оценка |
|---|---|---|
| Coding (mid) | ~600K in + 120K out/день × 0.8 | ~$40–70/мес |
| Coding (strong/frontier) | та же база × 0.2 | ~$25–60/мес |
| Review, research, sales-контент (mid/fast) | — | ~$30–60/мес |
| Classification/routing (cheap @ $0.10–0.30/$0.50–2.50) | высокий объём, копейки | ~$3–8/мес |
| **Итого AI** | | **~$100–200/мес** |

**Суммарно MVP: ~$150–280/мес.** Потолок безопасности: дневной budget guard $15. Если реальный счёт превышает $400/мес — смотреть в model_runs, что маршрутизируется не туда (первый подозреваемый — длинные контексты на strong-моделях).

Примечание по риску цен: Gemini 4 Argon и GPT-5.6 Sol — на промо-тарифах, с декабря 2026 дорожают вдвое; в смету заложены цены после повышения. Haiku 5.5 дорожает в 5 раз на промптах >100K токенов — router обязан учитывать context_size.

## 7. Scaling plan

| Триггер | Действие |
|---|---|
| > 200 задач/день | worker-пулы на отдельном VPS; переход очереди с pg на Redis Streams (код очереди за интерфейсом) |
| Долгие workflows (>часов, человеческие паузы) мешают | Temporal для критичных workflows; orchestrator делегирует |
| Независимость от Tailscale control plane | Headscale на KZ |
| Второй tenant | onboarding из blueprints/, smoke-тест изоляции RLS в CI |
| Enterprise-tenant с требованием изоляции | dedicated schema или dedicated PG instance; слой миграций это допускает |
| LLM-счёт > $2000/мес | локальные open-weight для classification/extraction; batch API (50% скидка) для ночных задач |
| Команда людей появится | SSO для Tailscale, GitHub branch protection усиливается, CODEOWNERS |


================================================================================
# ФАЙЛ: docs/RED_TEAM_REVIEW.md
================================================================================

# RED TEAM REVIEW — критический разбор собственной архитектуры

Разбор по состоянию на драфт v0.1. Для каждой проблемы: severity и конкретное исправление.

## CRITICAL

### R1. Сложность системы превышает команду из нуля человек
28 таблиц, 8 агентов, 3 узла, 12 контейнеров — это правильная *целевая* картина, но если строить всё сразу, проект умрёт на этапе инфраструктуры.
**Исправление:** жёстко следовать ROADMAP: MVP-1 требует только 15 таблиц, 4 агентов (CTO, 2 dev, auditor), REVIEW-режим. Остальное мигрируется. Kill-criteria фазы 1: 5 недель. Уже отражено в ROADMAP, но требует дисциплины владельца — не добавлять scope.

### R2. Codex/Claude CLI как production-runtime — зависимость от условий вендоров
CLI-инструменты меняют флаги, лимиты, лицензионные условия; их headless-режимы — не SLA-продукт. Построение оркестрации вокруг конкретных CLI — хрупкая точка.
**Исправление:** agent-runner общается с исполнителями через адаптер-интерфейс (`run(task, worktree) -> report.json`), а не через конкретные флаги CLI. Замена Codex CLI на прямой API-агент или другой инструмент = новый адаптер, ядро не трогаем. Вынести это требование в ARCHITECTURE.md как инвариант.

### R3. Hash-chain аудита защищает только от тихой подделки, а не от злонамеренного админа
Кто контролирует БД, может пересчитать всю цепочку.
**Исправление:** ежедневный экспорт хвоста цепочки в WORM-bucket (уже есть) + внешний якорь: daily digest хеша отправляется владельцу в Telegram и сохраняется в git-тег. Пересчёт цепочки без обнаружения становится практически невозможен. Усилить формулировку в SECURITY.md §7.

## HIGH

### R4. Warm standby на KZ ничего не стоит только на бумаге
«Возможность поднять» ≠ «поднимется». Без регулярного DR-прогона реальный RTO неизвестен; типичный сюрприз — DNS TTL, забытые ключи, образы, которых нет на KZ.
**Исправление:** обязательный ежеквартальный прогон (есть в DR §5) + метрика `restore_test_success` в мониторинге. Признать честно: первый прогон покажет 8+ часов, а не 4.

### R5. Tailscale = единая точка входа и единая точка отказа для админ-доступа
Компрометация tailnet-аккаунта владельца (tag:admin) = доступ ко всем трём узлам.
**Исправление:** MFA на аккаунте, отдельный ACL: tag:admin только с конкретного устройства; критичные действия всё равно требуют approval-HMAC (второй фактор по сути). Headscale в v1.1 снимает и vendor-риск. Уже частично есть — зафиксировать MFA как обязательный пункт security checklist.

### R6. Sales-агент с доступом к исходящей почте — репутационный риск выше технического
Один галлюцинированный оффер клиенту дороже месяца работы системы.
**Исправление:** в MVP sales-agent имеет только `outbound.draft_only` (уже в agents.yaml). Первые 50 сообщений — 100% human review. Снятие ограничения — отдельным решением владельца после статистики quality review.

### R7. Данные РФ-пользователей и knowledge layer
152-ФЗ требует хранения персданных граждан РФ в РФ. Если лиды/клиенты РФ попадут в CRM на Spain PostgreSQL — формальное нарушение.
**Исправление:** поле `data_residency` в connector schema (есть) + правило: записи customers/leads/deals по РФ-клиентам физически хранятся в RU PostgreSQL, control-plane хранит только обезличенные ссылки. Это осознанное усложнение схемы CRM — принять в фазе 2, до запуска реальных продаж. Не юридическая консультация — требуется проверка у юриста перед запуском продаж в РФ.

### R8. Один владелец = bus factor 1
Все approvals, мастер-ключ, DNS, аккаунты провайдеров — на одном человеке.
**Исправление:** escrow: мастер-ключ age + инструкция восстановления у доверенного лица (есть в SECURITY.md §2); доверенное лицо с tag:admin-readonly в tailnet; документ «если владелец недоступен 7 дней» с процедурой. Добавить в DEPLOYMENT.md.

## MEDIUM

### R9. Approval через Telegram — зависимость от третьей стороны в критичном контуре
Telegram недоступен/заблокирован → approvals не работают → production deploy встаёт.
**Исправление:** fallback-канал: approvals через admin UI (уже предусмотрен дизайном — «ссылка на полный payload»). Оба канала в MVP.

### R10. n8n может подтянуться в «мозг» незаметно
Соблазн добавить «ещё один шаг в n8n» велик; через полгода бизнес-логика размазана.
**Исправление:** политика: n8n-workflow может содержать максимум 3 шага и не может писать в БД напрямую (нет сети до postgres — уже в compose). Review n8n-workflows — раз в месяц.

### R11. Смета AI не включает неэффективность агентных циклов
Coding-агент в реальности тратит 3–10x токенов против «одного вызова»: итерации, чтение файлов, неудачные тесты.
**Исправление:** в смету заложен множитель через разделение по классам, но реальный множитель узнаем только из `model_runs`. Budget guard $15/день — реальная защита, а смету корректировать после 2 недель данных, не экстраполировать теорию.

### R12. git worktrees на одном диске Spain — IO-конкуренция и дисковый лимит
N параллельных агентов × полная копия репо × node_modules.
**Исправление:** лимит параллелизма agent-runner (4 одновременных), очистка worktree после merge (cron), мониторинг диска с алертом 75%.

### R13. RLS — сильный механизм, но один забытый `ALTER TABLE … DISABLE RLS` или роль с BYPASSRLS обнуляет изоляцию
**Исправление:** CI-тест изоляции (уже в checklist) + аудит ролей БД в weekly job: кто имеет BYPASSRLS — только migrator, и это alarm, если изменится.

## LOW

### R14. Mermaid-диаграммы в Markdown не рендерятся везде
**Исправление:** принять: диаграммы читаемы как код; при публикации — экспорт через mermaid-cli в CI.

### R15. COMPETE-режим легко превращается в дорогую игрушку
Два strong-агента + auditor на каждую «неочевидную» задачу — $5–15 за задачу.
**Исправление:** COMPETE требует явного поля в задаче и бюджета ≥ $5; AI CTO эскалирует выбор COMPETE при частоте > 1/неделю — сигнал, что проблемы недодекомпозированы.

### R16. Красивые KPI без данных
«autonomous %», «revenue attribution» — метрики, которые на MVP нечем наполнить.
**Исправление:** dashboard MVP — только 2 блока (уже решено). Не показывать пустые виджеты — пустой дашборд деморализует и дискредитирует систему.

## Итог red team

Архитектура здоровая в направлении, но главный риск проекта — не технический: **переинжиниринг раньше первого бизнес-результата**. Все CRITICAL/HIGH сводятся к дисциплине: строить строго по фазам, резать scope, мерить реальные данные вместо теоретических. Технические исправления R2, R3, R5, R7 внесены или отмечены для внесения в соответствующие документы.


================================================================================
# ФАЙЛ: docs/FINAL_ANSWERS.md
================================================================================

# FINAL_ANSWERS — три контрольных вопроса

## A. Можно ли после реализации передать систему другой компании и развернуть новый tenant без переписывания ядра?

**Да, с оговоркой.** Архитектурные основания:

1. **tenant_id + PostgreSQL RLS** на каждой бизнес-таблице — изоляция на уровне СУБД, проверенная CI-тестом. Ядро не знает, сколько tenant'ов существует.
2. **Blueprint-система** (blueprint.schema.json + company.yaml): новая компания = новый файл blueprint (departments, agents, workflows, approval_policies, connectors). Процедура: создать tenant → применить blueprint → провести smoke-тест изоляции. Код ядра не меняется.
3. **Агенты, workflows, connectors — декларативные** (agent.yaml/workflow.yaml/manifest), а не код.
4. **Model Router** с реестром моделей — конфигурация, не код.

Оговорка: это верно для MVP-архитектуры *при условии*, что доменная логика пяти текущих контуров не просочится в ядро. Защита — правило: всё специфичное для бизнеса живёт только в blueprints/, workflows/, agents/; code review проверяет отсутствие хардкода tenant-специфики в services/. Это дисциплина, не технология — за ней нужен отдельный пункт в рубрике cross-review.

Полноценный «продукт для чужой компании» — это фаза 6 (onboarding UI, self-service, dedicated-DB опция). До неё «передать другой компании» = передать репозиторий + помощь в развёртывании, а не SaaS-регистрацию.

## B. Можно ли заменить OpenAI / Claude / Gemini без переписывания business workflows?

**Да.** Основания:

1. **Единственная точка вызова LLM — Model Router.** Агенты и workflows не знают, какая модель их обслуживает; они указывают `task_type`, `quality_required`, `privacy_level` — не имя модели.
2. **Реестр моделей** (models/registry.yaml): замена провайдера = новая запись + адаптер интерфейса (`complete(messages, params) -> {text, usage}`). Бизнес-workflow не затрагивается.
3. **Eval-статистика** (model_runs) привязана к task_type, а не к конкретной модели — router сам перераспределит трафик после замены, накопив score новой модели.
4. Codex/Claude **CLI как исполнители** — другая история (см. R2 red team): они привязаны к своим вендорам. Поэтому agent-runner изолирует их адаптером; workflow «code → review → deploy» переживёт замену исполнителя.

Практический предел: промпты неизбежно подстраиваются под особенности моделей. Системные инструкции агентов лежат в agents/prompts/ и версионируются — замена модели может потребовать ревизии промптов, но не переписывания workflows или кода оркестрации.

## C. Если Spain AI-node завтра полностью исчезнет, что именно нужно сделать, чтобы Казахстан продолжил работу?

Конкретная последовательность (детально — DISASTER_RECOVERY.md §4):

1. Зафиксировать границу потерь: время последней WAL-записи в бэкапе (RPO ≤ 15 мин).
2. На KZ: `restore-control-plane.sh --latest` — restic restore nightly base + WAL replay.
3. Расшифровать секреты KZ-контура (age-ключ kazakhstan уже на узле; LLM-ключи продублированы в его sops-файле).
4. `docker compose -f docker-compose.kz.yml up -d` — поднять orchestrator, model-router, agent-runner, n8n, monitoring (профиль standby→active).
5. Переключить DNS `api.<domain>` на KZ IP (human approval — DNS в списке критичных действий; TTL 300s заранее).
6. Проверить: /health, тестовая задача через очередь, связность deploy-broker'а KZ с RU (второй ключ deploy-ai уже в authorized_keys на RU).
7. Объявить Spain потерянным; при появлении нового сервера — install-spain.sh, обратная репликация, плановый возврат primary.

**Что не восстановится:** задачи в статусе `running` (перезапустятся по retry policy), staging-окружение (жертвуем).

**Честные оговорки:**
- RTO 2–4 часа — только после учебных прогонов. Первый реальный случай без тренировки займёт больше.
- Слабое звено — DNS и Telegram approvals: оба доступны владельцу с любого устройства, это ок.
- RU production продолжит работу весь период аварии автономно — правильное разделение контуров уже окупается.
- Критичное требование, без которого план не работает: мастер-ключ age офлайн у владельца и свежесть зеркал/бэкапов на KZ — за этим следит метрика `restore_test_success` и алерт при отставании зеркал > 1 часа.


================================================================================
# ФАЙЛ: schemas/task.schema.json
================================================================================

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://founder-ai-os/schemas/task.schema.json",
  "title": "Task Protocol",
  "type": "object",
  "required": ["task_id", "tenant_id", "project_id", "department", "goal", "why", "expected_output", "acceptance_criteria", "reviewer", "budget"],
  "properties": {
    "task_id": { "type": "string", "format": "uuid" },
    "tenant_id": { "type": "string", "format": "uuid" },
    "project_id": { "type": "string", "format": "uuid" },
    "department": { "type": "string", "enum": ["development", "sales", "content", "product", "operations", "client_success", "rnd", "executive"] },
    "parent_task_id": { "type": ["string", "null"], "format": "uuid" },
    "workflow_run_id": { "type": ["string", "null"], "format": "uuid" },
    "goal": { "type": "string", "minLength": 10 },
    "why": { "type": "string", "minLength": 10, "description": "Бизнес-причина. Задача без why не создаётся." },
    "input": { "type": "object", "default": {} },
    "context": {
      "type": "object",
      "properties": {
        "knowledge_refs": { "type": "array", "items": { "type": "string" } },
        "related_tasks": { "type": "array", "items": { "type": "string", "format": "uuid" } },
        "external_refs": { "type": "array", "items": { "type": "string", "format": "uri" } }
      },
      "default": {}
    },
    "expected_output": {
      "type": "object",
      "required": ["type", "description"],
      "properties": {
        "type": { "type": "string", "enum": ["code_change", "document", "analysis", "decision", "deal_result", "deployment", "dataset"] },
        "description": { "type": "string", "minLength": 10 },
        "artifacts": { "type": "array", "items": { "type": "string" }, "description": "Ожидаемые файлы/артефакты" }
      }
    },
    "acceptance_criteria": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["type", "description"],
        "properties": {
          "type": { "type": "string", "enum": ["test", "command", "http_check", "file_exists", "metric", "human_review"] },
          "description": { "type": "string" },
          "command": { "type": "string", "description": "Для type=command: команда, exit code 0 = pass" },
          "url": { "type": "string", "description": "Для type=http_check" },
          "expected_status": { "type": "integer" },
          "path": { "type": "string", "description": "Для type=file_exists" },
          "metric_code": { "type": "string" },
          "threshold": { "type": "number" }
        }
      }
    },
    "tools_allowed": { "type": "array", "items": { "type": "string" }, "default": [] },
    "permissions": { "type": "array", "items": { "type": "string" }, "default": [] },
    "mode": { "type": "string", "enum": ["SOLO", "PAIR", "PARALLEL", "REVIEW", "COMPETE"], "default": "REVIEW" },
    "primary_model": { "type": ["string", "null"] },
    "fallback_model": { "type": ["string", "null"] },
    "budget": {
      "type": "object",
      "required": ["max_usd"],
      "properties": {
        "max_usd": { "type": "number", "exclusiveMinimum": 0 },
        "max_tokens": { "type": ["integer", "null"] }
      }
    },
    "deadline": { "type": ["string", "null"], "format": "date-time" },
    "reviewer": { "type": "string", "description": "agent_id или user_id проверяющего. Не может совпадать с исполнителем." },
    "retry_policy": {
      "type": "object",
      "properties": {
        "max_attempts": { "type": "integer", "minimum": 1, "maximum": 5, "default": 2 },
        "backoff_seconds": { "type": "integer", "default": 300 }
      },
      "default": { "max_attempts": 2, "backoff_seconds": 300 }
    },
    "escalation_policy": {
      "type": "object",
      "properties": {
        "escalate_to": { "type": "string" },
        "after_attempts": { "type": "integer", "default": 2 },
        "on_budget_exceeded": { "type": "boolean", "default": true }
      },
      "default": {}
    },
    "requires_human_approval": {
      "type": "array",
      "items": { "type": "string", "enum": ["payment", "contract", "destructive_db", "dns", "auth_change", "secrets", "data_deletion", "high_risk_deploy", "public_statement"] },
      "default": []
    },
    "next_action": {
      "type": ["object", "null"],
      "properties": {
        "workflow_code": { "type": "string" },
        "task_template": { "type": "string" },
        "payload": { "type": "object" }
      },
      "default": null
    },
    "status": {
      "type": "string",
      "enum": ["created", "queued", "running", "blocked", "review", "rework", "approved", "failed", "completed", "cancelled"],
      "default": "created",
      "description": "Управляется только orchestrator'ом"
    }
  },
  "additionalProperties": false
}

```

================================================================================
# ФАЙЛ: schemas/task-v1.schema.json
================================================================================

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Founder AI OS — Task Protocol v1",
  "type": "object",
  "required": ["id", "project", "title", "goal", "inputs", "expected_output", "criteria", "owner"],
  "additionalProperties": false,
  "properties": {
    "id": {"type": "string", "pattern": "^[A-Z0-9][A-Z0-9_-]{1,79}$"},
    "project": {"type": "string", "description": "id из config/company.json"},
    "title": {"type": "string", "minLength": 3},
    "goal": {"type": "string", "minLength": 10, "description": "Зачем: измеримый бизнес-результат"},
    "why": {"type": "string", "description": "Какую дорогую работу заменяет или какой доход создаёт"},
    "inputs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    "expected_output": {"type": "string", "minLength": 5},
    "criteria": {"type": "string", "minLength": 5, "description": "Проверяемые критерии приёмки"},
    "tools_allowed": {"type": "array", "items": {"type": "string"}},
    "mode": {"enum": ["SOLO", "PAIR", "PARALLEL", "COMPETE", "REVIEW"], "default": "SOLO"},
    "model_hint": {"type": "string", "description": "Класс модели из config/model-router.json"},
    "budget_rub": {"type": ["number", "null"], "minimum": 0, "description": "null = платные вызовы заблокированы"},
    "deadline": {"type": "string", "format": "date"},
    "owner": {"type": "string", "description": "id роли-исполнителя из org/agents.json"},
    "human_approval": {"type": "boolean", "default": false, "description": "true = после ревью аудитора требуется подтверждение владельца"},
    "next_action": {"type": "string"}
  }
}

```

================================================================================
# ФАЙЛ: schemas/agent.schema.json
================================================================================

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://founder-ai-os/schemas/agent.schema.json",
  "title": "AI Agent Definition",
  "type": "object",
  "required": ["agent_id", "role", "goal", "department", "input_schema", "output_schema", "model_policy", "permissions", "budget", "kpi", "reviewer", "escalation_rule"],
  "properties": {
    "agent_id": { "type": "string", "pattern": "^[a-z0-9-]+$" },
    "role": { "type": "string", "description": "Ссылка на agent_roles.code" },
    "goal": { "type": "string", "minLength": 10 },
    "department": { "type": "string" },
    "system_instruction_ref": { "type": "string", "description": "Путь к файлу system instruction в /agents" },
    "input_schema": { "type": "object", "description": "JSON Schema входа агента" },
    "output_schema": { "type": "object", "description": "JSON Schema законченного продукта агента" },
    "skills": { "type": "array", "items": { "type": "string" }, "default": [] },
    "tools": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Whitelist tool ids из connector/manifests. Пустой массив = нет инструментов.",
      "default": []
    },
    "model_policy": {
      "type": "object",
      "required": ["task_type"],
      "properties": {
        "task_type": { "type": "string" },
        "quality_required": { "type": "string", "enum": ["low", "standard", "high", "critical"], "default": "standard" },
        "preferred_model": { "type": ["string", "null"], "default": null },
        "fallback_model": { "type": ["string", "null"], "default": null },
        "max_context": { "type": ["integer", "null"], "default": null }
      }
    },
    "permissions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Permission codes, напр. deploy.staging, crm.write"
    },
    "budget": {
      "type": "object",
      "required": ["monthly_usd"],
      "properties": {
        "monthly_usd": { "type": "number", "exclusiveMinimum": 0 },
        "per_task_usd": { "type": ["number", "null"], "default": null }
      }
    },
    "kpi": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["metric", "target"],
        "properties": {
          "metric": { "type": "string" },
          "target": { "type": ["number", "string"] },
          "period": { "type": "string", "enum": ["day", "week", "month"], "default": "week" }
        }
      }
    },
    "reviewer": { "type": "string", "description": "agent_id или user_id. Обязателен и не может быть самим агентом." },
    "escalation_rule": {
      "type": "object",
      "required": ["escalate_to"],
      "properties": {
        "escalate_to": { "type": "string" },
        "conditions": {
          "type": "array",
          "items": { "type": "string", "enum": ["budget_exceeded", "rework_cycles_exceeded", "blocked_timeout", "low_confidence", "security_scope"] },
          "minItems": 1
        }
      }
    },
    "failure_conditions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Условия, при которых агент считается неработающим",
      "default": []
    },
    "audit": {
      "type": "object",
      "properties": {
        "log_all_tool_calls": { "type": "boolean", "default": true },
        "log_full_prompts": { "type": "boolean", "default": false, "description": "Включать только для отладки; содержит данные" }
      },
      "default": { "log_all_tool_calls": true, "log_all_prompts": false }
    }
  },
  "additionalProperties": false
}

```

================================================================================
# ФАЙЛ: schemas/workflow.schema.json
================================================================================

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://founder-ai-os/schemas/workflow.schema.json",
  "title": "Workflow Definition",
  "type": "object",
  "required": ["code", "name", "version", "trigger", "steps", "done_definition"],
  "properties": {
    "code": { "type": "string", "pattern": "^[a-z0-9-]+$" },
    "name": { "type": "string" },
    "version": { "type": "integer", "minimum": 1 },
    "department": { "type": "string" },
    "trigger": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": { "type": "string", "enum": ["event", "schedule", "manual", "task_completed"] },
        "source": { "type": "string", "description": "connector code для event, cron для schedule" },
        "filter": { "type": "object" }
      }
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "type"],
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string", "enum": ["task", "approval", "condition", "wait", "parallel", "action"] },
          "task_template": { "type": "string", "description": "Для type=task: шаблон задачи" },
          "assignee_role": { "type": "string" },
          "depends_on": { "type": "array", "items": { "type": "string" }, "default": [] },
          "condition": { "type": "object", "description": "Для type=condition: выражение над контекстом workflow" },
          "wait_for": { "type": "object", "properties": { "duration": { "type": "string" }, "until_event": { "type": "string" } } },
          "on_failure": { "type": "string", "enum": ["fail_workflow", "retry", "escalate", "skip"], "default": "escalate" },
          "sla_hours": { "type": ["number", "null"], "default": null },
          "approval_type": { "type": ["string", "null"], "default": null }
        }
      }
    },
    "done_definition": {
      "type": "object",
      "required": ["description", "evidence"],
      "properties": {
        "description": { "type": "string", "description": "Что является законченным бизнес-результатом, напр. оплаченная сделка или зафиксированный отказ" },
        "evidence": { "type": "array", "items": { "type": "string" }, "description": "Машинно-проверяемые свидетельства: записи в БД, события, метрики" }
      }
    },
    "kpis": { "type": "array", "items": { "type": "string" }, "default": [] },
    "timeout_hours": { "type": ["number", "null"], "default": null }
  },
  "additionalProperties": false
}

```

================================================================================
# ФАЙЛ: schemas/connector.schema.json
================================================================================

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://founder-ai-os/schemas/connector.schema.json",
  "title": "Connector Manifest",
  "type": "object",
  "required": ["name", "version", "authentication", "actions", "data_scope", "audit_level"],
  "properties": {
    "name": { "type": "string", "pattern": "^[a-z0-9-]+$" },
    "version": { "type": "string" },
    "description": { "type": "string" },
    "authentication": {
      "type": "object",
      "required": ["type", "secret_refs"],
      "properties": {
        "type": { "type": "string", "enum": ["oauth2", "api_key", "service_account", "ssh_key", "webhook_secret", "bot_token"] },
        "secret_refs": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Ссылки на ключи в SOPS-файлах, напр. sops://spain/connectors#gmail_sa_key"
        },
        "scopes": { "type": "array", "items": { "type": "string" }, "default": [] }
      }
    },
    "actions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "description", "input_schema", "output_schema", "permission_required"],
        "properties": {
          "id": { "type": "string", "description": "напр. gmail.send, gdrive.read, telegram.notify" },
          "description": { "type": "string" },
          "input_schema": { "type": "object" },
          "output_schema": { "type": "object" },
          "permission_required": { "type": "string", "description": "Permission code, без которого action недоступен" },
          "mutating": { "type": "boolean", "default": false, "description": "Мутирующие действия логируются с payload" },
          "requires_approval": { "type": "boolean", "default": false }
        }
      }
    },
    "permissions_model": {
      "type": "object",
      "description": "Как connector выдаётся агентам: только явным назначением в agent.yaml + permission",
      "properties": {
        "auto_grant": { "type": "boolean", "const": false, "description": "Connector нельзя давать агенту автоматически — поле зафиксировано в false" }
      }
    },
    "data_scope": {
      "type": "object",
      "required": ["privacy_class"],
      "properties": {
        "privacy_class": { "type": "string", "enum": ["public", "internal", "confidential"] },
        "acl_tags": { "type": "array", "items": { "type": "string" }, "default": [] },
        "ru_data_residency": { "type": "boolean", "default": false, "description": "true = данные не покидают RU-контур" }
      }
    },
    "rate_limits": {
      "type": "object",
      "properties": {
        "requests_per_minute": { "type": "integer" },
        "burst": { "type": "integer" }
      },
      "default": {}
    },
    "audit_level": { "type": "string", "enum": ["metadata", "full_payload"], "description": "full_payload — только для не-confidential" }
  },
  "additionalProperties": false
}

```

================================================================================
# ФАЙЛ: schemas/blueprint.schema.json
================================================================================

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://founder-ai-os/schemas/blueprint.schema.json",
  "title": "Company Blueprint",
  "description": "Развёртывание компании/tenant из шаблона: departments, roles, agents, workflows, KPI, connectors, dashboards, approval policies",
  "type": "object",
  "required": ["blueprint_code", "name", "version", "business_units", "departments", "agents", "workflows", "approval_policies"],
  "properties": {
    "blueprint_code": { "type": "string", "pattern": "^[a-z0-9-]+$", "description": "напр. expert-business, business-community, ai-startup" },
    "name": { "type": "string" },
    "version": { "type": "string" },
    "business_units": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["code", "name"],
        "properties": {
          "code": { "type": "string" },
          "name": { "type": "string" },
          "owner": { "type": ["string", "null"], "default": null }
        }
      }
    },
    "departments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["code", "name", "business_unit", "done_definition"],
        "properties": {
          "code": { "type": "string" },
          "name": { "type": "string" },
          "business_unit": { "type": "string" },
          "done_definition": { "type": "string", "description": "Законченный продукт отдела, напр. работающий релиз или оплаченная сделка" },
          "default_kpi": { "type": "array", "items": { "type": "string" }, "default": [] }
        }
      }
    },
    "agents": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["agent_ref", "department"],
        "properties": {
          "agent_ref": { "type": "string", "description": "Ссылка на файл agent.yaml" },
          "department": { "type": "string" },
          "overrides": { "type": "object", "description": "Переопределения полей agent.yaml для этого blueprint" }
        }
      }
    },
    "workflows": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["workflow_ref"],
        "properties": {
          "workflow_ref": { "type": "string" },
          "enabled": { "type": "boolean", "default": true }
        }
      }
    },
    "connectors": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["connector", "enabled"],
        "properties": {
          "connector": { "type": "string" },
          "enabled": { "type": "boolean" },
          "config_overrides": { "type": "object", "default": {} }
        }
      },
      "default": []
    },
    "dashboards": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["code", "blocks"],
        "properties": {
          "code": { "type": "string" },
          "blocks": { "type": "array", "items": { "type": "string", "enum": ["revenue", "product", "development", "content", "operations", "rnd", "ai_company", "decisions_required"] } }
        }
      },
      "default": []
    },
    "approval_policies": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["trigger", "approver"],
        "properties": {
          "trigger": { "type": "string", "enum": ["payment", "contract", "destructive_db", "dns", "auth_change", "secrets", "data_deletion", "high_risk_deploy", "public_statement"] },
          "approver": { "type": "string", "description": "user_id или роль человека" },
          "expires_hours": { "type": "integer", "default": 24 },
          "require_confirmation_phrase": { "type": "boolean", "default": false }
        }
      }
    }
  },
  "additionalProperties": false
}

```

================================================================================
# ФАЙЛ: blueprints/company.yaml
================================================================================

```yaml
# BLUEPRINT: founder-company (первый tenant)
# Валидируется по schemas/blueprint.schema.json
blueprint_code: founder-company
name: Founder Company (5 контуров)
version: "0.2"

business_units:
  - { code: personal-brand, name: "Личный бренд / Анастасия" }
  - { code: proyavlennost, name: "Проявленность" }
  - { code: yardniki, name: "Ярдники" }
  - { code: vforume, name: "ВФОРУМЕ" }
  - { code: rnd-lab, name: "R&D / Startup Lab" }

departments:
  - code: content
    name: "Редакция «Сила малых групп» (Content & Growth)"
    business_unit: proyavlennost
    done_definition: "Опубликованный качественный материал с карточкой (source, theme, audience, product, funnel_stage, CTA) и измеренными leads/meetings/pipeline; материал сохранён в Knowledge Base"
    default_kpi: [published_per_week, leads_from_content, assets_per_source, voice_match_score]
  - code: development
    name: Development Department
    business_unit: vforume
    done_definition: "Работающий релиз: acceptance criteria, тесты, staging, healthcheck, rollback, changelog, audit"
    default_kpi: [release_success_rate, failed_tests_count, incidents_count]
  - code: sales
    name: Sales Department
    business_unit: proyavlennost
    done_definition: "Оплаченная сделка ИЛИ зафиксированный отказ (reason, next_contact_date, probability)"
    default_kpi: [deals_won, pipeline_value, followup_sla]
  - code: security
    name: Security Center
    business_unit: personal-brand
    done_definition: "Горизонтальный контроль: weekly security report + немедленные critical alerts; ни одного необъяснённого инцидента"
    default_kpi: [critical_alert_latency_minutes, unresolved_high_findings_over_14d]
  - code: finance
    name: Finance Department
    business_unit: personal-brand
    done_definition: "Financial Decision System: P&L по BU, 13-недельный cash flow, kill rules срабатывают, 11 вопросов получают ответ из данных"
    default_kpi: [forecast_accuracy, cash_runway_weeks, founder_attention_roi]
    # агенты подключаются: finance-lite в P2, полный отдел в P5
  - code: customer-intelligence
    name: Customer & Market Intelligence
    business_unit: proyavlennost
    done_definition: "Доказанные insights (evidence_level=pattern) с willingness_to_pay — до любых marketing/sales задач"
    default_kpi: [pattern_insights_per_month, wtp_evidence_coverage]
  - code: marketing
    name: Marketing Department
    business_unit: proyavlennost
    done_definition: "Qualified demand: leads, meetings, pipeline, revenue с атрибуцией в CRM — не охваты и не посты"
    default_kpi: [qualified_leads, cac, pipeline_from_marketing]
  - code: executive
    name: Executive
    business_unit: personal-brand
    done_definition: "Принятое решение с зафиксированными assumptions и evidence; weekly decision pack без остатка 'в тексте'"
    default_kpi: [decisions_closed, decision_latency_hours]

agents:
  # P0/P4 — ядро и разработка
  - { agent_ref: agents/ai-ceo.yaml,                department: executive }
  - { agent_ref: agents/ai-cto.yaml,                department: development }
  - { agent_ref: agents/codex-developer.yaml,       department: development }
  - { agent_ref: agents/claude-developer.yaml,      department: development }
  - { agent_ref: agents/reviewer-auditor.yaml,      department: development }
  - { agent_ref: agents/operations-controller.yaml, department: executive }
  # P1 — редакция «Сила малых групп»
  - { agent_ref: agents/editor-in-chief.yaml,          department: content }
  - { agent_ref: agents/knowledge-miner.yaml,          department: content }
  - { agent_ref: agents/smg-writer.yaml,               department: content }
  - { agent_ref: agents/anastasia-voice.yaml,          department: content }
  - { agent_ref: agents/quality-critic.yaml,           department: content }
  - { agent_ref: agents/confidentiality-reviewer.yaml, department: content }
  - { agent_ref: agents/distribution-growth.yaml,      department: content }
  # Security (горизонтальный контур, не подчинён development)
  - { agent_ref: agents/ai-ciso.yaml,               department: security }
  # P3 — продажи
  - { agent_ref: agents/sales-researcher.yaml,      department: sales }
  - { agent_ref: agents/sales-agent.yaml,           department: sales }

workflows:
  - { workflow_ref: workflows/editorial-pipeline.yaml,        enabled: true }   # P1
  - { workflow_ref: workflows/weekly-executive-meeting.yaml,  enabled: true }   # управленческий ритм
  - { workflow_ref: workflows/mvp1-code-to-production.yaml,   enabled: true }   # P4
  - { workflow_ref: workflows/mvp2-lead-to-deal.yaml,         enabled: false }  # P3, включается с Sales

connectors:
  - { connector: telegram, enabled: true }
  - { connector: github,   enabled: true }
  - { connector: gdrive,   enabled: true }    # P1: источник редакции
  - { connector: gmail,    enabled: false }   # P3

dashboards:
  - code: ceo
    blocks: [ai_company, decisions_required, content, development, operations]
    # revenue/product/rnd включаются по мере появления данных; GREY лучше пустого блока

approval_policies:
  - { trigger: payment,          approver: owner, expires_hours: 24, require_confirmation_phrase: true }
  - { trigger: contract,         approver: owner, expires_hours: 48 }
  - { trigger: destructive_db,   approver: owner, expires_hours: 12, require_confirmation_phrase: true }
  - { trigger: dns,              approver: owner, expires_hours: 12 }
  - { trigger: auth_change,      approver: owner, expires_hours: 24 }
  - { trigger: secrets,          approver: owner, expires_hours: 12 }
  - { trigger: data_deletion,    approver: owner, expires_hours: 24, require_confirmation_phrase: true }
  - { trigger: high_risk_deploy, approver: owner, expires_hours: 8 }
  - { trigger: public_statement, approver: owner, expires_hours: 72 }

```

================================================================================
# ФАЙЛ: blueprints/councils.yaml
================================================================================

```yaml
# Четыре совета компании (§65–70). Машинно-читаемый каталог.
# ЖЁСТКОЕ ПРАВИЛО: оптики построены только на публичных книгах, интервью,
# акционерных письмах, выступлениях и проверяемых кейсах. Система НЕ утверждает,
# что реальные люди участвуют в компании, НЕ имитирует их личности и НЕ придумывает
# их мнение. Lens = документированный паттерн мышления + источники.

councils:

  executive:
    question: "Что делать сейчас?"
    trigger: weekly   # weekly-executive-meeting workflow
    composition: [ai-ceo, cfo, cro, cmo, cpo, cto, coo, ai-ciso, chief-decision-scientist]
    output: weekly_executive_decision_pack

  entrepreneurial:
    question: "Где деньги и масштаб?"
    trigger: on_demand   # новая бизнес-модель, ценообразование, большие инвестиции,
                         # новый продукт, смена стратегии, закрытие проекта, масштабирование
    process: [fact_pack, financial_model, customer_evidence, lenses_3_to_5, critique, contradictions, decision_options]
    output: "OPTION A/B/C + expected value + risks + reversibility + recommendation + evidence (формирует AI CEO; НЕ голосование)"
    lenses:
      - { id: hartmann,    name: "Оскар Хартманн",   optics: "скорость действия, портфель гипотез, массовое тестирование, закрытие неработающего, асимметричные возможности", key_question: "Что мы можем проверить быстрее и дешевле прямо сейчас?" }
      - { id: kuchment,    name: "Михаил Кучмент",   optics: "эффективность, P&L, расходы, омниканальность, фокус, производительность капитала", key_question: "Как сделать эту модель экономически эффективнее?" }
      - { id: sedov,       name: "Владимир Седов / Askona", optics: "глубокая потребительская боль, вертикальная интеграция, долгий горизонт, экосистемы", key_question: "Какую потребность клиента мы ещё не увидели?" }
      - { id: galitsky,    name: "Сергей Галицкий",  optics: "клиент, ритейл-экономика, простота, масштаб, операционная дисциплина", key_question: "Что реально важно покупателю и можно ли это масштабировать?" }
      - { id: gref,        name: "Герман Греф",      optics: "цифровая трансформация, технологии, AI, организационное масштабирование, метрики", key_question: "Как превратить это из локального проекта в систему?" }
      - { id: fridman,     name: "Михаил Фридман",   optics: "капитал, сделки, структура собственности, портфель, risk/reward", key_question: "Стоит ли этот актив вложенного капитала и риска?" }
      - { id: bezos,       name: "Jeff Bezos",       optics: "customer obsession, long-term, flywheel, free cash flow, high-velocity decisions", key_question: "Что станет лучше для клиента, если мы сделаем это?" }
      - { id: huang,       name: "Jensen Huang",     optics: "platform shift, technology inflection points, долгий горизонт, скорость исполнения, экосистема", key_question: "Это локальная функция или новая технологическая платформа?" }
      - { id: collison,    name: "Patrick Collison", optics: "economic infrastructure, developer experience, internet economics, removing friction", key_question: "Как убрать ещё один слой трения для клиента?" }
      - { id: lutke,       name: "Tobi Lütke",       optics: "entrepreneur platform, product engineering, merchant success, ecosystem", key_question: "Помогает ли наш продукт клиенту самому больше зарабатывать?" }
      - { id: chesky,      name: "Brian Chesky",     optics: "product experience, design, trust, community, founder-led product", key_question: "Какой опыт получает человек от начала до конца?" }
      - { id: hastings,    name: "Reed Hastings",    optics: "talent density, context over control, organizational speed, culture", key_question: "Нужен ли здесь контроль или достаточно правильного контекста и сильного человека?" }

  creative:
    question: "Что ещё возможно?"
    trigger: on_demand   # важные продуктовые/стратегические задачи, до оценки реалистичности
    rule: "Первые 20% процесса ограничения не обсуждаются. Divergence до convergence. Совет НЕ утверждает инвестиции."
    process:
      - "минимум 10 существенно различных направлений"
      - "аналогии из других индустрий"
      - "стресс-вопросы: без текущей бизнес-модели? / в 10 раз дешевле? / в 10 раз дороже? / без людей? / без интерфейса? / оплата только за результат? / почти нулевой капитал?"
      - "после divergence: Product Council → Finance → Customer Research → Technical Feasibility → TEST"
    lenses:
      - { id: ive,      name: "Jony Ive",      optics: "простота, целостность, качество продукта" }
      - { id: catmull,  name: "Ed Catmull",    optics: "творческая среда, честная обратная связь, усиление слабой идеи" }
      - { id: chesky_c, name: "Brian Chesky",  optics: "дизайн опыта и бизнеса одновременно" }
      - { id: bezos_c,  name: "Jeff Bezos",    optics: "идеи вокруг будущих потребностей клиента" }
      - { id: rubin,    name: "Rick Rubin",    optics: "отсечение лишнего, сила сути" }
      - { id: dyson,    name: "James Dyson",   optics: "экспериментирование и прототипы" }
      - { id: jobs,     name: "Steve Jobs",    optics: "историческая продуктовая оптика: технология × продукт × человеческий опыт" }
    internal_roles: [futurist, crazy-ideas-agent, cross-industry-analogy-agent, business-model-inventor, technology-scout, customer-future-agent]

  risk_audit:
    question: "Почему это может провалиться?"
    trigger: before_major_decision
    composition: [ai-ciso, reviewer-auditor, financial-auditor]
    output: "риски по severity + kill criteria + что должно быть правдой, чтобы решение оказалось неверным"

separation_rule: "Советы не смешиваются в одном запуске. Иначе творческая идея будет убита финансистом на первой минуте, либо безумная идея уйдёт в производство без проверки."

```

================================================================================
# ФАЙЛ: blueprints/agents/ai-ceo.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: ai-ceo
role: ai_ceo
goal: "Управлять портфелем задач компании: приоритизация, распределение по отделам, контроль законченных бизнес-результатов, подготовка решений для владельца"
department: executive
system_instruction_ref: agents/prompts/ai-ceo.md

input_schema:
  type: object
  properties:
    portfolio_snapshot: { type: object }
    pending_decisions: { type: array }
    kpi_delta: { type: object }

output_schema:
  type: object
  required: [prioritized_tasks, owner_decisions]
  properties:
    prioritized_tasks: { type: array, description: "Задачи с приоритетом и назначенным отделом" }
    owner_decisions:
      type: array
      description: "Не более 5–7 вопросов, каждый с options/tradeoffs/recommendation"
    blocked_analysis: { type: array }

skills: [portfolio-management, prioritization, decision-framing]
tools: [tasks.read, tasks.create, tasks.reprioritize, metrics.read, approvals.request]
permissions: [tasks.manage.all, metrics.read, approvals.request]
model_policy:
  task_type: decision_analysis
  quality_required: high
  preferred_model: null   # выбирает router (strong-класс)
budget: { monthly_usd: 60, per_task_usd: 2 }
kpi:
  - { metric: tasks_completed_vs_planned, target: 0.85, period: week }
  - { metric: owner_decision_latency_hours, target: 24, period: week }
reviewer: owner
escalation_rule:
  escalate_to: owner
  conditions: [blocked_timeout, low_confidence]
failure_conditions:
  - "Более 20% задач недели завершились без законченного продукта"
  - "Очередь blocked > 5 задач дольше 48 часов без эскалации"

```

================================================================================
# ФАЙЛ: blueprints/agents/ai-ciso.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: ai-ciso
role: security_officer
goal: "Горизонтальный контур безопасности всей компании: не разрабатывает продукт — защищает систему. Security Center, weekly security report, немедленные алерты по critical"
department: security
system_instruction_ref: agents/prompts/ai-ciso.md

input_schema:
  type: object
  properties:
    window_hours: { type: integer, default: 168 }
    triggered_by: { type: string, enum: [schedule, alert], default: schedule }

output_schema:
  type: object
  required: [security_report]
  properties:
    security_report:
      type: object
      properties:
        incidents: { type: array }
        vulnerabilities: { type: array }
        access_anomalies: { type: array }
        outdated_components: { type: array }
        backup_failures: { type: array }
        unusual_ai_behaviour: { type: array }
        prompt_injection_attempts: { type: array }
        recommended_changes: { type: array }
    immediate_alerts: { type: array }

skills: [security-monitoring, anomaly-detection, audit-analysis]
tools: [audit_logs.read, security_events.read, metrics.read, alerts.send_critical, router.call]
permissions: [audit.read, security.read_all, alerts.send]
# Только read + alerts. Никаких изменений системы — remediation через задачи и approvals.
model_policy:
  task_type: review
  quality_required: high
budget: { monthly_usd: 30, per_task_usd: 1 }
kpi:
  - { metric: critical_alert_latency_minutes, target: 5, period: week }
  - { metric: weekly_report_on_time, target: 1, period: month }
  - { metric: unresolved_high_findings_over_14d, target: 0, period: month }
reviewer: owner
escalation_rule:
  escalate_to: owner
  conditions: [security_scope, blocked_timeout]
failure_conditions:
  - "Critical event не стал алертом немедленно (попал только в weekly report)"
  - "Изменение системы напрямую, минуя approval"
scope_note: "Security Center видит: auth events, permission changes, failed logins, API key usage, SSH events, deploys, production access, unusual model usage, data exports, connector activity, suspicious agent behaviour, prompt injection attempts, backup status, security updates, open vulnerabilities"

```

================================================================================
# ФАЙЛ: blueprints/agents/ai-cto.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: ai-cto
role: ai_cto
goal: "Техническое руководство: декомпозиция задач, выбор режима Codex/Claude (SOLO/PAIR/PARALLEL/REVIEW/COMPETE), архитектурные решения, контроль Definition of Done"
department: development
system_instruction_ref: agents/prompts/ai-cto.md

input_schema:
  type: object
  required: [task]
  properties:
    task: { type: object, description: "Задача по task.schema.json" }
    repo_context: { type: object }

output_schema:
  type: object
  required: [mode, subtasks]
  properties:
    mode: { type: string, enum: [SOLO, PAIR, PARALLEL, REVIEW, COMPETE] }
    subtasks:
      type: array
      items:
        type: object
        required: [goal, assignee, acceptance_criteria]
        properties:
          goal: { type: string }
          assignee: { type: string, enum: [codex-developer, claude-developer] }
          acceptance_criteria: { type: array }
    architecture_notes: { type: string }

skills: [architecture, decomposition, code-review-design, risk-analysis]
tools: [tasks.read, tasks.create_subtask, git.read, knowledge.read]
permissions: [tasks.manage.development, repo.read, knowledge.read.internal]
model_policy:
  task_type: architecture
  quality_required: high
budget: { monthly_usd: 80, per_task_usd: 3 }
kpi:
  - { metric: release_success_rate, target: 0.95, period: week }
  - { metric: rework_cycles_avg, target: 1.5, period: week }
reviewer: reviewer-auditor
escalation_rule:
  escalate_to: owner
  conditions: [security_scope, low_confidence]
failure_conditions:
  - "Задача ушла в работу без машинно-проверяемых acceptance criteria"
  - "Режим COMPETE выбран для задачи с очевидным решением (перерасход)"

```

================================================================================
# ФАЙЛ: blueprints/agents/anastasia-voice.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: anastasia-voice
role: voice_editor
goal: "Приведение текста к голосу Анастасии: лексика, ритм, характер, убрать всё нехарактерное; финальная редактура перед критиком"
department: content
system_instruction_ref: agents/prompts/anastasia-voice.md

input_schema:
  type: object
  required: [content_item_id, draft_ref]
  properties:
    content_item_id: { type: string }
    draft_ref: { type: string }

output_schema:
  type: object
  required: [edited_ref, voice_diff_summary]
  properties:
    edited_ref: { type: string }
    voice_diff_summary: { type: string, description: "Что изменено и почему — для калибровки" }

skills: [editing, voice-matching, style]
tools: [knowledge.read_voice_reference, content.write_draft, router.call]
permissions: [knowledge.read.voice_reference, content.write_draft]
# voice-reference — корпус эталонных текстов Анастасии (acl_tag voice-reference)
model_policy:
  task_type: writing
  quality_required: high
budget: { monthly_usd: 40, per_task_usd: 1 }
kpi:
  - { metric: voice_match_score, target: 8, period: month, description: "Оценка quality-critic по оси Brand Fit" }
  - { metric: owner_rewrite_rate, target: 0.2, period: month, description: "Доля материалов, которые собственник переписывает сама" }
reviewer: quality-critic
escalation_rule:
  escalate_to: editor-in-chief
  conditions: [rework_cycles_exceeded]
failure_conditions:
  - "Голос изменён в сторону 'универсального экспертного стиля'"
  - "Потерян смысл утверждения из draft при правке"

```

================================================================================
# ФАЙЛ: blueprints/agents/claude-developer.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: claude-developer
role: developer
goal: "Реализация задач разработки и независимое code review работ Codex; в режиме PAIR — со-архитектор"
department: development
system_instruction_ref: agents/prompts/claude-developer.md

input_schema:
  type: object
  required: [task, worktree]
  properties:
    task: { type: object }
    worktree: { type: string }
    review_patch: { type: ["string", "null"], description: "Заполняется в режиме REVIEW" }

output_schema:
  type: object
  required: [report_json]
  properties:
    report_json: { type: object }
    branch: { type: ["string", "null"] }
    review:
      type: ["object", "null"]
      properties:
        verdict: { type: string, enum: [approve, request_changes] }
        findings:
          type: array
          items:
            type: object
            required: [severity, issue]
            properties:
              severity: { type: string, enum: [blocker, major, minor] }
              file: { type: string }
              lines: { type: string }
              issue: { type: string }
              suggestion: { type: string }

skills: [frontend, backend, code-review, tests, security-basics]
tools: [git.write_own_worktree, git.read_other_branches, shell.sandboxed, tests.run, router.call]
permissions: [repo.write.own_branch, repo.read.all, staging.none, production.none]
model_policy:
  task_type: frontend_coding
  quality_required: standard
budget: { monthly_usd: 120, per_task_usd: 4 }
kpi:
  - { metric: review_findings_precision, target: 0.8, period: month }
  - { metric: first_pass_acceptance_rate, target: 0.7, period: week }
reviewer: codex-developer
escalation_rule:
  escalate_to: ai-cto
  conditions: [budget_exceeded, rework_cycles_exceeded, blocked_timeout]
failure_conditions:
  - "Approve без фактической проверки acceptance criteria"
  - "Изменения вне scope задачи в diff"
  - "Секрет или креды в коммите"

```

================================================================================
# ФАЙЛ: blueprints/agents/codex-developer.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: codex-developer
role: developer
goal: "Реализация задач разработки в выделенном git worktree с полным прохождением Definition of Done"
department: development
system_instruction_ref: agents/prompts/codex-developer.md

input_schema:
  type: object
  required: [task, worktree]
  properties:
    task: { type: object }
    worktree: { type: string }
    repo: { type: string }

output_schema:
  type: object
  required: [report_json, branch]
  properties:
    report_json: { type: object, description: "Формат из CLAUDE.md/AGENTS.md" }
    branch: { type: string }
    patch_ref: { type: string }

skills: [backend, frontend, tests, refactoring]
tools: [git.write_own_worktree, shell.sandboxed, tests.run, router.call]
permissions: [repo.write.own_branch, staging.none, production.none]
model_policy:
  task_type: backend_coding
  quality_required: standard
budget: { monthly_usd: 120, per_task_usd: 4 }
kpi:
  - { metric: first_pass_acceptance_rate, target: 0.7, period: week }
  - { metric: avg_cost_per_completed_task, target: 3, period: month }
reviewer: claude-developer    # по умолчанию REVIEW выполняет Claude; и наоборот
escalation_rule:
  escalate_to: ai-cto
  conditions: [budget_exceeded, rework_cycles_exceeded, blocked_timeout]
failure_conditions:
  - "Изменения вне scope задачи в diff"
  - "Секрет или креды в коммите"
  - "Тесты пропущены или подогнаны"

```

================================================================================
# ФАЙЛ: blueprints/agents/confidentiality-reviewer.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: confidentiality-reviewer
role: ethics_confidentiality_reviewer
goal: "Защита участников и групп: ни один материал не публикуется с данными, позволяющими идентифицировать человека или группу без разрешения. Veto-право"
department: content
system_instruction_ref: agents/prompts/confidentiality-reviewer.md

input_schema:
  type: object
  required: [content_item_id, edited_ref]
  properties:
    content_item_id: { type: string }
    edited_ref: { type: string }
    source_findings: { type: array, description: "Находки, на которых основан материал, с privacy_class" }

output_schema:
  type: object
  required: [verdict]
  properties:
    verdict: { type: string, enum: [pass, block, requires_owner_decision] }
    findings:
      type: array
      items:
        type: object
        properties:
          fragment: { type: string }
          risk: { type: string, enum: [identifiable_person, identifiable_group, context_reconstruction, missing_consent] }
          recommendation: { type: string }
    consents_checked: { type: array, description: "Ссылки на зафиксированные разрешения в CRM" }

skills: [ethics, deidentification, consent-verification]
tools: [content.read, crm.read_consents, router.call]
permissions: [content.read, crm.read_consents]
# НЕ подотчётен editor-in-chief. Эскалация только к собственнику.
model_policy:
  task_type: review
  quality_required: critical
  privacy_level: confidential
budget: { monthly_usd: 30, per_task_usd: 1 }
kpi:
  - { metric: confidentiality_incidents, target: 0, period: month }
  - { metric: false_positive_block_rate, target: 0.3, period: month, description: "Слишком высокий = переблокировка, смотреть калибровку" }
reviewer: owner
escalation_rule:
  escalate_to: owner
  conditions: [low_confidence, security_scope]
failure_conditions:
  - "Пропуск идентифицируемого фрагмента"
  - "verdict=pass при отсутствии проверки consents для материала на основе кейса"
note: "Veto этого агента не отменяется никем, кроме собственника. Его модель — отдельный провайдер от писателя и критика где возможно."

```

================================================================================
# ФАЙЛ: blueprints/agents/distribution-growth.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: distribution-growth
role: distribution_growth
goal: "Публикация по approve, дистрибуция, CTA, атрибуция лидов к материалам, аналитика эффективности контента до pipeline"
department: content
system_instruction_ref: agents/prompts/distribution-growth.md

input_schema:
  type: object
  required: [content_item_id]
  properties:
    content_item_id: { type: string }
    approved: { type: boolean }
    channel: { type: string }

output_schema:
  type: object
  properties:
    publication: { type: object, properties: { channel: { type: string }, url: { type: string }, published_at: { type: string }, utm: { type: object } } }
    performance_report: { type: object, properties: { reactions: { type: integer }, leads: { type: integer }, meetings: { type: integer }, pipeline: { type: number } } }
    repurpose_suggestions: { type: array }

skills: [distribution, analytics, attribution]
tools: [telegram.publish_approved, content.change_status, crm.read, crm.write_attribution, metrics.write, router.call]
permissions: [content.publish_approved, crm.read, metrics.write]
# Публикация ТОЛЬКО при approved=true (после owner approval). Сам approval дать не может.
model_policy:
  task_type: classification
  quality_required: standard
budget: { monthly_usd: 30, per_task_usd: 0.5 }
kpi:
  - { metric: leads_from_content, target: 5, period: month }
  - { metric: attribution_coverage, target: 0.8, period: month, description: "Доля лидов с известным content_item_id" }
reviewer: editor-in-chief
escalation_rule:
  escalate_to: editor-in-chief
  conditions: [blocked_timeout]
failure_conditions:
  - "Публикация без owner approval в audit_logs"
  - "Материал published без CTA и UTM"

```

================================================================================
# ФАЙЛ: blueprints/agents/editor-in-chief.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: editor-in-chief
role: content_director
goal: "Управление редакцией «Сила малых групп»: редакционные приоритеты, календарь, приёмка материалов, связь контента с бизнес-целями Проявленности"
department: content
system_instruction_ref: agents/prompts/editor-in-chief.md

input_schema:
  type: object
  properties:
    calendar_snapshot: { type: object }
    backlog_ideas: { type: array }
    performance_stats: { type: object }

output_schema:
  type: object
  required: [priorities]
  properties:
    priorities: { type: array, items: { type: object, properties: { content_item_id: { type: string }, priority: { type: integer }, why: { type: string } } } }
    calendar_changes: { type: array }
    escalations: { type: array }

skills: [editorial-management, prioritization, funnel-thinking]
tools: [content.read_all, content.change_status, tasks.create, metrics.read, knowledge.read, router.call]
permissions: [content.manage, knowledge.read.internal, tasks.create.content]
model_policy:
  task_type: decision_analysis
  quality_required: standard
budget: { monthly_usd: 40, per_task_usd: 1 }
kpi:
  - { metric: published_per_week, target: 3, period: week }
  - { metric: leads_from_content, target: 5, period: month }
  - { metric: assets_per_source, target: 3, period: month }
reviewer: ai-ceo
escalation_rule:
  escalate_to: ai-ceo
  conditions: [blocked_timeout, low_confidence]
failure_conditions:
  - "Материал ушёл в owner_review без content score"
  - "Календарь пуст дольше 3 дней при наличии источников"

```

================================================================================
# ФАЙЛ: blueprints/agents/knowledge-miner.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: knowledge-miner
role: knowledge_miner
goal: "Добыча сырья для редакции: инсайты, истории, исследования из источников (Drive, транскрипты, анкеты, кейсы) с обязательной классификацией конфиденциальности"
department: content
system_instruction_ref: agents/prompts/knowledge-miner.md

input_schema:
  type: object
  required: [source_ref]
  properties:
    source_id: { type: string }
    source_ref: { type: string }
    mining_focus: { type: ["string", "null"] }

output_schema:
  type: object
  required: [findings]
  properties:
    findings:
      type: array
      items:
        type: object
        required: [type, content, privacy_class, source_ref]
        properties:
          type: { type: string, enum: [insight, story, research_note, quote, question] }
          content: { type: string }
          privacy_class: { type: string, enum: [public, internal, confidential] }
          anonymized: { type: boolean }
          source_ref: { type: string }
          themes: { type: array, items: { type: string } }

skills: [mining, research, classification, anonymization-check]
tools: [gdrive.read, knowledge.write, knowledge.read, anonymizer.run, router.call]
permissions: [knowledge.read.assigned, knowledge.write.findings]
# НЕТ доступа к production DB, SSH, secrets. Только назначенные источники.
model_policy:
  task_type: research
  quality_required: standard
budget: { monthly_usd: 40, per_task_usd: 0.5 }
kpi:
  - { metric: usable_findings_per_source, target: 2, period: week }
  - { metric: privacy_classification_errors, target: 0, period: month }
reviewer: editor-in-chief
escalation_rule:
  escalate_to: confidentiality-reviewer
  conditions: [low_confidence, security_scope]
failure_conditions:
  - "confidential-материал ушёл в findings без anonymized=true"
  - "Цитата без source_ref"

```

================================================================================
# ФАЙЛ: blueprints/agents/operations-controller.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: operations-controller
role: operations_controller
goal: "Контроль исполнения всех workflow: deadlines, SLA, waiting states, зависимости, ретраи, разблокировка или эскалация зависших процессов"
department: executive
system_instruction_ref: agents/prompts/operations-controller.md

input_schema:
  type: object
  properties:
    window_hours: { type: integer, default: 24 }

output_schema:
  type: object
  required: [health_report]
  properties:
    health_report:
      type: object
      properties:
        workflows_on_track: { type: integer }
        workflows_at_risk: { type: array }
        blocked_tasks: { type: array }
        sla_breaches: { type: array }
    actions_taken: { type: array, description: "Автоматические разблокировки/ретраи по policy" }
    escalations: { type: array }

skills: [process-monitoring, sla-management, exception-handling]
tools: [tasks.read, tasks.retry, workflows.read, workflows.nudge, metrics.read, telegram.notify_owner, router.call]
permissions: [tasks.retry, workflows.read.all, workflows.nudge, alerts.send]
model_policy:
  task_type: classification
  quality_required: low    # мониторинг — детерминированная логика + cheap-модель для summary
budget: { monthly_usd: 20, per_task_usd: 0.2 }
kpi:
  - { metric: blocked_tasks_over_48h, target: 0, period: week }
  - { metric: sla_breach_rate, target: 0.05, period: week }
reviewer: ai-ceo
escalation_rule:
  escalate_to: owner
  conditions: [blocked_timeout]
failure_conditions:
  - "Workflow в blocked > 48 часов без эскалации"
  - "Автоматический retry вне retry_policy задачи"
note: "Большая часть логики — детерминированный код orchestrator'а; этот агент — семантический слой для summary и эскалаций, не дублирование кода LLM'ом"

```

================================================================================
# ФАЙЛ: blueprints/agents/quality-critic.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: quality-critic
role: content_critic
goal: "Независимая проверка качества: anti-AI filter, fact check, content score. Имеет право вернуть материал на переработку"
department: content
system_instruction_ref: agents/prompts/quality-critic.md

input_schema:
  type: object
  required: [content_item_id, edited_ref, claims]
  properties:
    content_item_id: { type: string }
    edited_ref: { type: string }
    claims: { type: array }

output_schema:
  type: object
  required: [verdict, content_score]
  properties:
    verdict: { type: string, enum: [approve, rework] }
    content_score:
      type: object
      properties:
        originality: { type: number, minimum: 0, maximum: 10 }
        expertise_depth: { type: number, minimum: 0, maximum: 10 }
        evidence_quality: { type: number, minimum: 0, maximum: 10 }
        relevance: { type: number, minimum: 0, maximum: 10 }
        emotional_impact: { type: number, minimum: 0, maximum: 10 }
        brand_fit: { type: number, minimum: 0, maximum: 10 }
        commercial_potential: { type: number, minimum: 0, maximum: 10 }
        reputational_risk: { type: number, minimum: 0, maximum: 10 }
    anti_ai_findings: { type: array, items: { type: string } }
    fact_check_results:
      type: array
      items:
        type: object
        properties:
          claim: { type: string }
          verdict: { type: string, enum: [verified, unverified, false] }
          source: { type: ["string", "null"] }

skills: [criticism, fact-checking, style-analysis]
tools: [web.search, knowledge.read, content.read, router.call]
permissions: [content.read, knowledge.read.anonymized, web.search]
model_policy:
  task_type: review
  quality_required: high
  # КРИТИЧНО: модель критика != модель писателя (правило из model-router: review не автором)
budget: { monthly_usd: 40, per_task_usd: 1 }
kpi:
  - { metric: false_facts_reaching_publication, target: 0, period: month }
  - { metric: rework_precision, target: 0.7, period: month, description: "Доля rework, которые признаны обоснованными" }
reviewer: editor-in-chief
escalation_rule:
  escalate_to: editor-in-chief
  conditions: [rework_cycles_exceeded]
failure_conditions:
  - "approve при reputational_risk >= 7 без пометки к owner review"
  - "claim со статусом verified без source"

```

================================================================================
# ФАЙЛ: blueprints/agents/reviewer-auditor.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: reviewer-auditor
role: reviewer_auditor
goal: "Независимая финальная проверка: соответствие Definition of Done, безопасность, арбитраж в режиме COMPETE, целостность аудита"
department: development
system_instruction_ref: agents/prompts/reviewer-auditor.md

input_schema:
  type: object
  required: [task_id]
  properties:
    task_id: { type: string }
    compete_variants: { type: ["array", "null"], description: "Заполняется в режиме COMPETE" }

output_schema:
  type: object
  required: [verdict]
  properties:
    verdict: { type: string, enum: [approve, request_changes, escalate_to_human] }
    dod_checklist: { type: object, description: "Каждый пункт DoD: pass/fail + evidence" }
    compete_decision:
      type: ["object", "null"]
      properties:
        winner: { type: string }
        rationale: { type: string }
        scores: { type: object }
    security_flags: { type: array }

skills: [audit, security-review, code-review, arbitration]
tools: [git.read_all, tests.run, audit_logs.read, router.call]
permissions: [repo.read.all, audit.read, staging.read]
model_policy:
  task_type: review
  quality_required: high
  preferred_model: null   # strong-класс, и ВСЕГДА другой провайдер, чем у автора кода
budget: { monthly_usd: 60, per_task_usd: 2 }
kpi:
  - { metric: escaped_defects, target: 0, period: month, description: "Дефекты, дошедшие до production после approve" }
  - { metric: audit_chain_integrity, target: 1, period: week }
reviewer: owner
escalation_rule:
  escalate_to: owner
  conditions: [security_scope, low_confidence]
failure_conditions:
  - "Approve кода, который не прошёл CI (обход pipeline)"
  - "Арбитраж COMPETE без сравнения по рубрике"

```

================================================================================
# ФАЙЛ: blueprints/agents/sales-agent.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: sales-agent
role: sales_agent
goal: "Ведение лида от квалификации до результата: персонализированный контакт, follow-up, встреча, предложение — до оплаченной сделки или зафиксированного отказа"
department: sales
system_instruction_ref: agents/prompts/sales-agent.md

input_schema:
  type: object
  required: [lead_id]
  properties:
    lead_id: { type: string }
    qualification: { type: object }
    history: { type: array }

output_schema:
  type: object
  required: [outcome]
  properties:
    outcome:
      type: object
      required: [type]
      properties:
        type: { type: string, enum: [deal_won, meeting_booked, follow_up_scheduled, lost] }
        lost_reason: { type: ["string", "null"] }
        next_contact_date: { type: ["string", "null"], format: date }
        probability: { type: ["number", "null"] }
    messages_sent: { type: array }

skills: [sales-copywriting, objection-handling, crm-management]
tools: [crm.read, crm.write, telegram.send_approved, gmail.send_approved, router.call]
permissions: [crm.read, crm.write, outbound.draft_only]
# ВАЖНО: исходящие сообщения — только draft + human approval (public_statement).
# Прямая отправка запрещена permissions outbound.draft_only.
model_policy:
  task_type: writing
  quality_required: standard
budget: { monthly_usd: 50, per_task_usd: 1 }
kpi:
  - { metric: meetings_booked, target: 4, period: month }
  - { metric: deals_won, target: 1, period: month }
  - { metric: followup_sla_compliance, target: 0.95, period: week }
reviewer: ai-ceo
escalation_rule:
  escalate_to: owner
  conditions: [low_confidence, security_scope]
failure_conditions:
  - "Отправка сообщения без approval"
  - "Лид закрыт без lost_reason/next_contact_date"
  - "Обещания клиенту, не согласованные с продуктом"

```

================================================================================
# ФАЙЛ: blueprints/agents/sales-researcher.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: sales-researcher
role: lead_researcher
goal: "Исследование лидов: обогащение данных, квалификация по ICP, подготовка фактуры для персонализации"
department: sales
system_instruction_ref: agents/prompts/sales-researcher.md

input_schema:
  type: object
  required: [lead_id]
  properties:
    lead_id: { type: string }

output_schema:
  type: object
  required: [qualification]
  properties:
    qualification:
      type: object
      required: [icp_fit, score, evidence]
      properties:
        icp_fit: { type: boolean }
        score: { type: number, minimum: 0, maximum: 100 }
        evidence: { type: array, items: { type: string }, description: "Ссылки/факты, на которых основан score" }
        pain_hypothesis: { type: string }
    enrichment: { type: object }

skills: [web-research, data-enrichment, icp-analysis]
tools: [web.search, crm.read, crm.write_enrichment, router.call]
permissions: [crm.read, crm.write_enrichment]
model_policy:
  task_type: research
  quality_required: standard
budget: { monthly_usd: 40, per_task_usd: 0.5 }
kpi:
  - { metric: qualification_precision, target: 0.7, period: month, description: "Доля qualified, дошедших до встречи" }
  - { metric: research_cost_per_lead, target: 0.5, period: month }
reviewer: sales-agent
escalation_rule:
  escalate_to: sales-agent
  conditions: [low_confidence, blocked_timeout]
failure_conditions:
  - "Score без evidence"
  - "Данные лида выдуманы (hallucinated company facts)"

```

================================================================================
# ФАЙЛ: blueprints/agents/smg-writer.yaml
================================================================================

```yaml
# Валидируется по schemas/agent.schema.json
agent_id: smg-writer
role: writer
goal: "Создание черновиков материалов редакции: структура, аргументация, методологическая точность, опора на добытые находки"
department: content
system_instruction_ref: agents/prompts/smg-writer.md

input_schema:
  type: object
  required: [content_item_id, brief]
  properties:
    content_item_id: { type: string }
    brief:
      type: object
      required: [theme, audience, product, funnel_stage, cta]
      properties:
        theme: { type: string }
        audience: { type: string }
        product: { type: string }
        funnel_stage: { type: string }
        cta: { type: string }
        findings_refs: { type: array }

output_schema:
  type: object
  required: [draft_ref]
  properties:
    draft_ref: { type: string }
    used_sources: { type: array }
    claims: { type: array, items: { type: string }, description: "Все проверяемые утверждения — вход для fact check" }

skills: [longform-writing, methodology, argumentation]
tools: [knowledge.read, content.write_draft, router.call]
permissions: [knowledge.read.anonymized, content.write_draft]
# Видит ТОЛЬКО обезличенную knowledge base. Никаких production DB, secrets, исходных транскриптов.
model_policy:
  task_type: writing
  quality_required: high
budget: { monthly_usd: 60, per_task_usd: 1.5 }
kpi:
  - { metric: drafts_passing_critic_first_try, target: 0.5, period: month }
  - { metric: methodology_errors_found, target: 0, period: month }
reviewer: anastasia-voice
escalation_rule:
  escalate_to: editor-in-chief
  conditions: [rework_cycles_exceeded, blocked_timeout]
failure_conditions:
  - "Утверждение без источника в claims"
  - "Выдуманная цитата или кейс"

```

================================================================================
# ФАЙЛ: workflows/editorial-pipeline.yaml
================================================================================

```yaml
# Валидируется по schemas/workflow.schema.json
code: editorial-pipeline
name: "Редакционный конвейер «Сила малых групп»"
version: 1
department: content
trigger:
  type: manual
  # также запускается событием ingestion.completed из knowledge layer
steps:
  - id: ingest
    type: task
    task_template: editorial-ingest
    assignee_role: knowledge_miner
    sla_hours: 24
  - id: mining
    type: task
    task_template: editorial-mining
    assignee_role: knowledge_miner
    depends_on: [ingest]
  - id: idea
    type: task
    task_template: editorial-idea
    assignee_role: knowledge_miner
    depends_on: [mining]
  - id: prioritize
    type: task
    task_template: editorial-prioritize
    assignee_role: content_director
    depends_on: [idea]
    sla_hours: 48
  - id: draft
    type: task
    task_template: editorial-draft
    assignee_role: writer
    depends_on: [prioritize]
    on_failure: retry
  - id: voice
    type: task
    task_template: editorial-voice
    assignee_role: voice_editor
    depends_on: [draft]
  - id: critic
    type: task
    task_template: editorial-critic
    assignee_role: content_critic
    depends_on: [voice]
    # verdict=rework -> orchestrator возвращает на draft (max 2 цикла)
  - id: confidentiality
    type: task
    task_template: editorial-confidentiality
    assignee_role: ethics_confidentiality_reviewer
    depends_on: [critic]
    on_failure: escalate
    # verdict=block -> workflow fails; veto не отменяется
  - id: owner_approval
    type: approval
    approval_type: public_statement
    depends_on: [confidentiality]
  - id: publish
    type: task
    task_template: editorial-publish
    assignee_role: distribution_growth
    depends_on: [owner_approval]
  - id: measure
    type: wait
    depends_on: [publish]
    wait_for: { duration: 168h }   # неделя измерений
  - id: analytics
    type: task
    task_template: editorial-analytics
    assignee_role: distribution_growth
    depends_on: [measure]
done_definition:
  description: "Опубликованный качественный материал с заполненной карточкой (source, theme, audience, product, funnel_stage, CTA, канал, дата) и измеренными результатами (leads, reactions, meetings, pipeline), плюс сохранённый интеллектуальный материал в Knowledge Base"
  evidence:
    - "content_items.status = 'published' ИЛИ 'measuring'"
    - "запись публикации с URL и UTM"
    - "approval record (public_statement) approved"
    - "метрики leads/reactions записаны в metrics"
kpis: [published_per_week, leads_from_content, assets_per_source, voice_match_score]
timeout_hours: 720

```

================================================================================
# ФАЙЛ: workflows/mvp1-code-to-production.yaml
================================================================================

```yaml
# Валидируется по schemas/workflow.schema.json
code: mvp1-code-to-production
name: "MVP-1: кодовая задача end-to-end до production"
version: 1
department: development
trigger:
  type: manual
steps:
  - id: cto_decompose
    type: task
    task_template: cto-decompose
    assignee_role: ai_cto
    sla_hours: 4
  - id: implement
    type: task
    task_template: dev-implement
    assignee_role: developer
    depends_on: [cto_decompose]
    # worktree, Codex/Claude по выбранному режиму
  - id: cross_review
    type: task
    task_template: dev-cross-review
    assignee_role: developer
    depends_on: [implement]
    # reviewer != автор; max 2 цикла rework
  - id: ci
    type: action
    depends_on: [cross_review]
    # lint, typecheck, unit, integration, build image
    on_failure: fail_workflow
  - id: staging
    type: action
    depends_on: [ci]
    # deploy staging + e2e + healthcheck
    on_failure: fail_workflow
  - id: security_review
    type: task
    task_template: security-review
    assignee_role: reviewer_auditor
    depends_on: [staging]
  - id: prod_approval
    type: approval
    approval_type: high_risk_deploy
    depends_on: [security_review]
    sla_hours: 8
  - id: production
    type: action
    depends_on: [prod_approval]
    # deploy-broker -> RU -> healthcheck; при fail — автоматический rollback + incident
    on_failure: escalate
done_definition:
  description: "Функция работает на RU production, healthcheck зелёный, весь след в audit_logs, rollback проверен"
  evidence:
    - "deployments.status = 'success' с healthcheck_result = pass"
    - "CI run зелёный, cross-review approve зафиксирован"
    - "approval record high_risk_deploy approved"
kpis: [release_success_rate, time_task_to_production]
timeout_hours: 72

```

================================================================================
# ФАЙЛ: workflows/mvp2-lead-to-deal.yaml
================================================================================

```yaml
# Валидируется по schemas/workflow.schema.json
code: mvp2-lead-to-deal
name: "MVP-2: лид → результат (сделка или зафиксированный отказ)"
version: 1
department: sales
trigger:
  type: event
  source: n8n-webhook-lead   # также: CTA из контента редакции (P3)
steps:
  - id: research
    type: task
    task_template: lead-research
    assignee_role: lead_researcher
    sla_hours: 24
  - id: qualify
    type: condition
    depends_on: [research]
    condition: { field: qualification.icp_fit, equals: true }
    # false -> фиксация отказа (lost, reason=not_icp) и завершение
  - id: contact
    type: task
    task_template: lead-contact
    assignee_role: sales_agent
    depends_on: [qualify]
    # исходящее сообщение — только draft + owner approval
  - id: follow_up
    type: wait
    depends_on: [contact]
    wait_for: { until_event: lead_reply, duration: 72h }
    # по таймауту — повторный follow-up (max 3, потом lost/no_reply)
  - id: close
    type: task
    task_template: lead-close
    assignee_role: sales_agent
    depends_on: [follow_up]
    sla_hours: 48
done_definition:
  description: "Оплаченная сделка ИЛИ чётко зафиксированный отказ: reason, next_contact_date, probability, данные"
  evidence:
    - "deals.status IN ('won','lost')"
    - "при lost: заполнены lost_reason, next_contact_date, probability"
kpis: [deals_won, meetings_booked, followup_sla_compliance]
timeout_hours: 720

```

================================================================================
# ФАЙЛ: workflows/weekly-executive-meeting.yaml
================================================================================

```yaml
# Валидируется по schemas/workflow.schema.json
code: weekly-executive-meeting
name: "Weekly Executive Meeting"
version: 1
department: executive
trigger:
  type: schedule
  source: "17 8 * * 1"   # понедельник 08:17 Europe/Moscow (off-peak minute)
steps:
  - id: dept_reports
    type: parallel
    # каждый подшаг — task dept-weekly-report для активных отделов;
    # отсутствующий отдел = статус GREY, не ошибка
    depends_on: []
    sla_hours: 2
  - id: synthesis
    type: task
    task_template: weekly-synthesis
    assignee_role: ai_ceo
    depends_on: [dept_reports]
    # cross-department analysis, conflict detection, bottleneck, financial effect, prioritization
  - id: decision_pack
    type: task
    task_template: weekly-decision-pack
    assignee_role: ai_ceo
    depends_on: [synthesis]
  - id: owner_decisions
    type: approval
    approval_type: public_statement   # временно; выделить тип owner_weekly_decisions при реализации
    depends_on: [decision_pack]
    sla_hours: 72
    # блок DECISIONS REQUIRED FROM ANASTASIA, максимум 5–7 пунктов
  - id: create_tasks
    type: action
    depends_on: [owner_decisions]
    # orchestrator: каждое решение -> задача (owner, deadline, KPI, контроль на следующей неделе)
done_definition:
  description: "Weekly Executive Decision Pack сохранён, каждое решение превращено в задачу с владельцем и дедлайном; ни одно решение не осталось только в тексте"
  evidence:
    - "документ decision pack в documents"
    - "задачи созданы и связаны с decisions"
    - "блок решений собственника отправлен, ответы зафиксированы"
kpis: [decisions_closed_within_week, tasks_from_pack_completed]
timeout_hours: 96

```

================================================================================
# ФАЙЛ: infra/docker-compose.yml
================================================================================

```yaml
# Founder AI OS — Spain primary node (control plane)
# Все порты — только внутренние docker-сети или tailnet. Наружу смотрит только caddy (443).
name: founder-ai-os

networks:
  internal:        # postgres/redis — только здесь
  proxy:           # caddy + публичные API
  monitoring:

volumes:
  pgdata:
  redis-data:
  grafana-data:
  loki-data:
  prometheus-data:
  n8n-data:
  worktrees:       # git worktrees для agent-runner

services:
  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    networks: [internal]
    environment:
      POSTGRES_USER: ${PG_APP_USER}
      POSTGRES_PASSWORD: ${PG_APP_PASSWORD}
      POSTGRES_DB: ${PG_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./postgres/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PG_APP_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks: [internal]
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes: [redis-data:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s

  orchestrator:
    image: ${REGISTRY}/orchestrator:${IMAGE_TAG}
    restart: unless-stopped
    networks: [internal, proxy, monitoring]
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    environment:
      DATABASE_URL: postgresql://${PG_APP_USER}:${PG_APP_PASSWORD}@postgres:5432/${PG_DB}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      MODEL_ROUTER_URL: http://model-router:8100
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_OWNER_CHAT_ID: ${TELEGRAM_OWNER_CHAT_ID}
      APPROVAL_HMAC_SECRET: ${APPROVAL_HMAC_SECRET}
      DAILY_AI_BUDGET_USD: ${DAILY_AI_BUDGET_USD:-15}
    # НЕ публикуем порт наружу — доступ через caddy

  model-router:
    image: ${REGISTRY}/model-router:${IMAGE_TAG}
    restart: unless-stopped
    networks: [internal]
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
      DATABASE_URL: postgresql://${PG_APP_USER}:${PG_APP_PASSWORD}@postgres:5432/${PG_DB}
      REGISTRY_CONFIG: /config/models.yaml
    volumes:
      - ./models:/config:ro

  knowledge:
    image: ${REGISTRY}/knowledge:${IMAGE_TAG}
    restart: unless-stopped
    networks: [internal]
    depends_on: [postgres]
    environment:
      DATABASE_URL: postgresql://${PG_APP_USER}:${PG_APP_PASSWORD}@postgres:5432/${PG_DB}

  n8n:
    image: n8nio/n8n:latest
    restart: unless-stopped
    networks: [internal, proxy]
    environment:
      N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY}
      WEBHOOK_URL: https://hooks.${DOMAIN}/
      ORCHESTRATOR_URL: http://orchestrator:8000
      # n8n НЕ имеет доступа к postgres — только к orchestrator API
    volumes: [n8n-data:/home/node/.n8n]

  agent-runner:
    image: ${REGISTRY}/agent-runner:${IMAGE_TAG}
    restart: unless-stopped
    networks: [internal]
    depends_on: [orchestrator]
    security_opt: [no-new-privileges:true]
    cap_drop: [ALL]
    read_only: true
    tmpfs: [/tmp:size=2g]
    volumes:
      - worktrees:/srv/worktrees
      - ./agent-runner/egress-allowlist.txt:/config/egress-allowlist.txt:ro
    environment:
      ORCHESTRATOR_URL: http://orchestrator:8000
      GIT_REMOTE: ${GIT_REMOTE}
      # LLM-ключей здесь НЕТ — агенты вызывают model-router через orchestrator

  deploy-broker:
    image: ${REGISTRY}/deploy-broker:${IMAGE_TAG}
    restart: unless-stopped
    networks: [internal]
    volumes:
      - ${DEPLOY_SSH_KEY_PATH}:/keys/deploy_ai:ro
    environment:
      RU_NODE: deploy-ai@ru-node.tailnet
      ALLOWED_COMMANDS: "deploy rollback healthcheck"

  restic:
    image: restic/restic:latest
    restart: "no"
    networks: [internal]
    profiles: [backup]
    volumes:
      - pgdata:/backup/pgdata:ro
    environment:
      RESTIC_REPOSITORY: ${RESTIC_REPOSITORY}
      RESTIC_PASSWORD: ${RESTIC_PASSWORD}
      AWS_ACCESS_KEY_ID: ${B2_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${B2_APPLICATION_KEY}
    entrypoint: ["/bin/sh", "/scripts/backup.sh"]
    # Запуск по cron с хоста: docker compose run --rm restic

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    networks: [proxy]
    ports:
      - "443:443"
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data

  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    networks: [monitoring, internal]
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus

  loki:
    image: grafana/loki:latest
    restart: unless-stopped
    networks: [monitoring]
    volumes: [loki-data:/loki]

  promtail:
    image: grafana/promtail:latest
    restart: unless-stopped
    networks: [monitoring]
    volumes:
      - /var/log:/var/log:ro
      - ./monitoring/promtail.yml:/etc/promtail/config.yml:ro

  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    networks: [monitoring, proxy]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
    volumes: [grafana-data:/var/lib/grafana]

  node-exporter:
    image: prom/node-exporter:latest
    restart: unless-stopped
    networks: [monitoring]

volumes:
  caddy-data:

```

================================================================================
# ФАЙЛ: infra/.env.example
================================================================================

```bash
# ==========================================================================
# Founder AI OS — шаблон переменных. Реальные значения — ТОЛЬКО через SOPS.
# Этот файл коммитится. Значения ниже — плейсхолдеры, не секреты.
# ==========================================================================

# --- Общие ---
DOMAIN=example.com
REGISTRY=ghcr.io/your-org
IMAGE_TAG=latest
GIT_REMOTE=git@github.com:your-org/founder-ai-os.git

# --- PostgreSQL ---
PG_APP_USER=faios_app
PG_APP_PASSWORD=__SOPS__
PG_DB=founder_ai_os

# --- Redis ---
REDIS_PASSWORD=__SOPS__

# --- LLM providers (только Spain / KZ-standby) ---
OPENAI_API_KEY=__SOPS__
ANTHROPIC_API_KEY=__SOPS__
GOOGLE_API_KEY=__SOPS__

# --- Telegram (alerts + approvals) ---
TELEGRAM_BOT_TOKEN=__SOPS__
TELEGRAM_OWNER_CHAT_ID=__SOPS__
APPROVAL_HMAC_SECRET=__SOPS__

# --- Budget guards ---
DAILY_AI_BUDGET_USD=15

# --- n8n ---
N8N_ENCRYPTION_KEY=__SOPS__

# --- Backups (restic -> off-provider object storage) ---
RESTIC_REPOSITORY=s3:https://s3.us-west-004.backblazeb2.com/founder-ai-backups
RESTIC_PASSWORD=__SOPS__
B2_KEY_ID=__SOPS__
B2_APPLICATION_KEY=__SOPS__

# --- Deploy broker ---
DEPLOY_SSH_KEY_PATH=/run/secrets/deploy_ai_key

# --- Grafana ---
GRAFANA_ADMIN_PASSWORD=__SOPS__

# --- Tailscale (используется install-скриптами, не compose) ---
# TAILSCALE_AUTH_KEY=__SOPS__

```

================================================================================
# ФАЙЛ: infra/bootstrap/install-kazakhstan.sh
================================================================================

```bash
#!/usr/bin/env bash
# ==========================================================================
# install-kazakhstan.sh — bootstrap SECONDARY AI NODE (warm standby)
# Принцип: PULL-модель. KZ сам забирает бэкапы/зеркала с внешних источников.
# Живых production-сервисов здесь нет до активации DR-сценария.
# ==========================================================================
set -euo pipefail
IFS=$'\n\t'

NODE_ROLE="kazakhstan"
APP_DIR="/opt/founder-ai-os"
LOG="/var/log/install-${NODE_ROLE}.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== [$(date -Is)] Bootstrap ${NODE_ROLE} node (warm standby) ==="

[[ $EUID -eq 0 ]] || { echo "Нужен root"; exit 1; }
[[ -f /root/.config/sops/age/keys.txt ]] || {
  echo "Положите age-ключ kazakhstan в /root/.config/sops/age/keys.txt"; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git jq ufw fail2ban restic \
  python3 python3-venv

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

# SOPS
if ! command -v sops >/dev/null; then
  SOPS_VER="3.9.0"
  curl -fsSLo /usr/local/bin/sops \
    "https://github.com/getsops/sops/releases/download/v${SOPS_VER}/sops-v${SOPS_VER}.linux.amd64"
  chmod +x /usr/local/bin/sops
fi

useradd -m -s /bin/bash ops 2>/dev/null || true
cat > /etc/ssh/sshd_config.d/90-founder.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
AllowUsers ops
EOF
systemctl reload ssh

ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0
ufw --force enable

systemctl enable --now fail2ban

if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi

# --- Репозитории: зеркала (сначала код — в нём лежат sops-секреты узла) -------
mkdir -p "$APP_DIR" /srv/git-mirror /srv/backups
git clone git@github.com:your-org/founder-ai-os.git "$APP_DIR" 2>/dev/null || git -C "$APP_DIR" pull --ff-only

TS_KEY=$(sops -d --extract '["tailscale_auth_key"]' "${APP_DIR}/infra/secrets/${NODE_ROLE}.enc.yaml")
tailscale up --auth-key="${TS_KEY}" --hostname=kz-node --advertise-tags=tag:standby
unset TS_KEY

for repo in founder-ai-os vforume infrastructure; do
  if [[ ! -d "/srv/git-mirror/${repo}.git" ]]; then
    git clone --mirror "git@github.com:your-org/${repo}.git" "/srv/git-mirror/${repo}.git"
  fi
done

# --- Cron: зеркала + pull бэкапов + ежемесячный restore test ----------------
cat > /etc/cron.d/founder-standby <<'EOF'
*/15 * * * * root for r in /srv/git-mirror/*.git; do git -C "$r" remote update --prune; done >> /var/log/git-mirror.log 2>&1
30 4 * * * root /opt/founder-ai-os/scripts/pull-backups.sh >> /var/log/pull-backups.log 2>&1
0 6 1 * * root /opt/founder-ai-os/scripts/restore-test.sh >> /var/log/restore-test.log 2>&1
EOF

# --- Конфигурация для активации (готова, но не запущена) ---------------------
cd "$APP_DIR"
[[ -f "infra/secrets/${NODE_ROLE}.enc.yaml" ]] && {
  sops -d "infra/secrets/${NODE_ROLE}.enc.yaml" > infra/.env.kz
  chmod 600 infra/.env.kz
}

echo "=== [$(date -Is)] Kazakhstan standby готов. Активация: docs/DISASTER_RECOVERY.md §4 ==="

```

================================================================================
# ФАЙЛ: infra/bootstrap/install-russia.sh
================================================================================

```bash
#!/usr/bin/env bash
# ==========================================================================
# install-russia.sh — bootstrap PRODUCTION NODE (Russia)
# На этом узле НЕТ: LLM-ключей, AI-агентов, доступа к control-plane БД.
# Только: reverse proxy, production runtime, deploy-broker-exec, бэкапы.
# ==========================================================================
set -euo pipefail
IFS=$'\n\t'

NODE_ROLE="russia"
APP_DIR="/opt/founder-ai-os"
LOG="/var/log/install-${NODE_ROLE}.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== [$(date -Is)] Bootstrap ${NODE_ROLE} node (production) ==="

[[ $EUID -eq 0 ]] || { echo "Нужен root"; exit 1; }
[[ -f /root/.config/sops/age/keys.txt ]] || {
  echo "Положите age-ключ russia в /root/.config/sops/age/keys.txt"; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git jq ufw fail2ban restic

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

if ! command -v sops >/dev/null; then
  SOPS_VER="3.9.0"
  curl -fsSLo /usr/local/bin/sops \
    "https://github.com/getsops/sops/releases/download/v${SOPS_VER}/sops-v${SOPS_VER}.linux.amd64"
  chmod +x /usr/local/bin/sops
fi

# --- Пользователи ------------------------------------------------------------
useradd -m -s /bin/bash ops 2>/dev/null || true
# deploy-ai: ОГРАНИЧЕННЫЙ пользователь для AI-инициированных деплоев.
# Shell — forced command через authorized_keys; прямого shell нет.
useradd -m -s /bin/bash deploy-ai 2>/dev/null || true
mkdir -p /home/deploy-ai/.ssh

# --- SSH hardening -------------------------------------------------------------
cat > /etc/ssh/sshd_config.d/90-founder.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
AllowUsers ops deploy-ai
EOF
systemctl reload ssh

# --- Firewall: 80/443 снаружи, остальное только tailnet ------------------------
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow in on tailscale0
ufw --force enable
systemctl enable --now fail2ban

# --- Tailscale -------------------------------------------------------------------
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
mkdir -p "$APP_DIR"
git clone git@github.com:your-org/infrastructure.git "$APP_DIR" 2>/dev/null || git -C "$APP_DIR" pull --ff-only

TS_KEY=$(sops -d --extract '["tailscale_auth_key"]' "${APP_DIR}/secrets/${NODE_ROLE}.enc.yaml")
tailscale up --auth-key="${TS_KEY}" --hostname=ru-node --advertise-tags=tag:production
unset TS_KEY

# --- deploy-broker-exec: единственное, что умеет deploy-ai ----------------------
install -m 0755 "$APP_DIR/broker/deploy-broker-exec" /usr/local/bin/deploy-broker-exec
# authorized_keys: forced command. Публичные ключи брокера — из репозитория (не секреты).
{
  while read -r pubkey; do
    echo "command=\"/usr/local/bin/deploy-broker-exec\",no-pty,no-agent-forwarding,no-X11-forwarding ${pubkey}"
  done < "$APP_DIR/broker/allowed_deployers.pub"
} > /home/deploy-ai/.ssh/authorized_keys
chmod 700 /home/deploy-ai/.ssh && chmod 600 /home/deploy-ai/.ssh/authorized_keys
chown -R deploy-ai:deploy-ai /home/deploy-ai/.ssh

# deploy-ai может управлять ТОЛЬКО своим compose-проектом через wrapper,
# права на docker — через группу, sudo не выдаётся.
usermod -aG docker deploy-ai

# --- Production compose (ВФОРУМЕ и др.) -----------------------------------------
sops -d "${APP_DIR}/secrets/${NODE_ROLE}.enc.yaml" > "${APP_DIR}/.env"
chmod 600 "${APP_DIR}/.env"
cd "$APP_DIR"
docker compose -f docker-compose.ru.yml pull
docker compose -f docker-compose.ru.yml up -d

# --- Backup cron ------------------------------------------------------------------
cat > /etc/cron.d/founder-backup <<'EOF'
47 3 * * * root /opt/founder-ai-os/scripts/backup-ru.sh >> /var/log/restic-ru.log 2>&1
EOF

echo "=== [$(date -Is)] Russia production node готов ==="
echo "Проверка из Spain: ssh deploy-ai@ru-node 'healthcheck vforume'"

```

================================================================================
# ФАЙЛ: infra/bootstrap/install-spain.sh
================================================================================

```bash
#!/usr/bin/env bash
# ==========================================================================
# install-spain.sh — bootstrap PRIMARY AI NODE (Spain)
# Запуск: curl -sSL <repo>/install-spain.sh | bash   (от root на чистом Ubuntu 24.04)
# Секреты: только через SOPS. Скрипт не содержит и не запрашивает секреты в открытом виде.
# ==========================================================================
set -euo pipefail
IFS=$'\n\t'

NODE_ROLE="spain"
APP_DIR="/opt/founder-ai-os"
LOG="/var/log/install-${NODE_ROLE}.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== [$(date -Is)] Bootstrap ${NODE_ROLE} node ==="

# --- 0. Предусловия -------------------------------------------------------
[[ $EUID -eq 0 ]] || { echo "Нужен root"; exit 1; }
[[ -f /root/.config/sops/age/keys.txt ]] || {
  echo "Положите age-ключ узла в /root/.config/sops/age/keys.txt и перезапустите"; exit 1; }

# --- 1. Базовая система ---------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git jq unzip ufw fail2ban \
  python3 python3-venv python3-pip \
  unattended-upgrades apt-listchanges

# Node.js LTS
if ! command -v node >/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
  apt-get install -y nodejs
fi

# Docker + Compose plugin
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null

# SOPS + age
if ! command -v sops >/dev/null; then
  SOPS_VER="3.9.0"
  curl -fsSLo /usr/local/bin/sops \
    "https://github.com/getsops/sops/releases/download/v${SOPS_VER}/sops-v${SOPS_VER}.linux.amd64"
  chmod +x /usr/local/bin/sops
fi
command -v age-keygen >/dev/null || apt-get install -y age || true

# --- 2. Пользователи ------------------------------------------------------
useradd -m -s /bin/bash ops 2>/dev/null || true
useradd -r -s /usr/sbin/nologin monitor 2>/dev/null || true
# deploy-ai на этом узле не нужен (он на RU); Spain сам ходит наружу через deploy-broker

# --- 3. SSH hardening -----------------------------------------------------
cat > /etc/ssh/sshd_config.d/90-founder.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
AllowUsers ops
EOF
systemctl reload ssh

# --- 4. Firewall: наружу только 443 (caddy) и SSH из tailnet --------------
ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0
ufw allow 443/tcp
ufw --force enable

# --- 5. Fail2ban + автообновления ----------------------------------------
systemctl enable --now fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades

# --- 6. Tailscale (установка; подключение — после git clone, т.к. auth key в sops-файле репо) ---
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi

# --- 7. Код и конфигурация -------------------------------------------------
mkdir -p "$APP_DIR" /srv/worktrees
git clone git@github.com:your-org/founder-ai-os.git "$APP_DIR" 2>/dev/null || git -C "$APP_DIR" pull --ff-only
cd "$APP_DIR"

# auth key берётся из sops-файла, НЕ из аргумента командной строки
TS_KEY=$(sops -d --extract '["tailscale_auth_key"]' "infra/secrets/${NODE_ROLE}.enc.yaml")
tailscale up --auth-key="${TS_KEY}" --hostname=es-node --advertise-tags=tag:control
unset TS_KEY

# Расшифровка секретов узла -> .env (0600, не коммитится)
sops -d "infra/secrets/${NODE_ROLE}.enc.yaml" > infra/.env
chmod 600 infra/.env

# --- 8. Запуск --------------------------------------------------------------
cd infra
docker compose pull
docker compose up -d

# Миграции БД
docker compose exec -T orchestrator alembic upgrade head

# --- 9. Backup cron -----------------------------------------------------------
cat > /etc/cron.d/founder-backup <<'EOF'
17 3 * * * root cd /opt/founder-ai-os/infra && docker compose run --rm restic >> /var/log/restic.log 2>&1
*/15 * * * * root /opt/founder-ai-os/scripts/wal-archive-push.sh >> /var/log/wal-archive.log 2>&1
EOF

# --- 10. Проверка ---------------------------------------------------------------
sleep 15
curl -fsS http://localhost:8000/health >/dev/null && echo "orchestrator: OK"
curl -fsS http://localhost:3000 >/dev/null && echo "grafana: OK"
echo "=== [$(date -Is)] Spain node готов. Health: https://api.${DOMAIN}/health ==="

```