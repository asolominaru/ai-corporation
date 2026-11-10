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
