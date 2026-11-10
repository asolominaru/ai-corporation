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
