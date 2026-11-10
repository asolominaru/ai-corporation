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
