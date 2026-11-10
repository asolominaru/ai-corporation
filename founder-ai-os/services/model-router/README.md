# Model Router — единая точка LLM-вызовов (P0.1)

Все обращения к моделям идут только через этот сервис. Секреты провайдеров
живут здесь (env), клиенты ключей не видят (K-12). Браузер/UI токенов
router'а не имеет — вызывает только orchestrator.

Версия 0.1.1 — доработка после повторной проверки 2026-11-06 (R-03, R-04).

## Запуск (dev)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ROUTER_TOKENS='{"tok-admin":{"actor":"admin","role":"admin"},
  "tok-orch":{"actor":"orch","role":"orchestrator","tenant_id":"<tenant>"}}'
export AI_DAILY_CAP_USD=15 AI_MONTHLY_CAP_USD=280
export OPENAI_API_KEY=...   # только на сервере
.venv/bin/uvicorn app.main:app --port 8200
```

## Тесты

```bash
.venv/bin/python -m pytest tests/ -q   # 11 passed, сеть заглушена
```

## Гарантии

- **Личность из токена** (ROUTER_TOKENS), не из тела. /models — только admin,
  /complete — только orchestrator с совпадающим tenant (R-03/R-04.1).
- **Allowlist endpoint'ов** (config.ALLOWED_BASE_URLS): проверяется и при
  регистрации модели, и непосредственно перед HTTP-вызовом — ключ провайдера
  физически не может уйти на неразрешённый URL (R-03).
- **Бюджет (R-04):** атомарный резерв на уровнях task+day+month
  (conditional UPDATE — гонки и перекрывающиеся вызовы одной задачи
  отклоняются); периоды фиксируются в резерве — переход через полночь не
  теряет траты; settlement идемпотентен; факт > оценки записывается честно
  (`overrun: true`), дальнейшие вызовы блокируются перерасходом.
- **Закон 7:** `task_budget_max_usd` отсутствует/0 → 402, провайдер
  не вызывается.
- **Privacy:** данные класса X — только в модели с privacy_class ≥ X
  (public < anonymized < personal_data < confidential).
- Каждый вызов пишется в `model_runs` (успех и ошибка).

## Лимиты

- AI_DAILY_CAP_USD=15, AI_MONTHLY_CAP_USD=280 — применяются ОБА; месячный
  связующий. ($15×30=$450 > $280 — расхождение сметы на решении владельца.)
- Цены моделей: поля price_verified_at/pricing_url; без них цена
  считается непроверенной (требование проверки к ROADMAP).

## Ограничения P0

- Оценка входных токенов — заявленная вызывающим (est_tokens_in); точный
  подсчёт токенизатором на сервере — следующая итерация.
- Fallback на запасную модель при 5xx — TODO.
- Router доверяет бюджету задачи, переданному orchestrator'ом (авторитетный
  источник — оркестратор); прямой обход router'а закрыт отсутствием токенов
  у других компонентов.
