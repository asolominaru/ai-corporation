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
