# Карта происхождения

| Файл | Происхождение |
|---|---|
| `10_Blueprint/AI_Corporation_Blueprint_v1.md` | Новый документ (02.11.2026) из чата «Организация команд и процессов» (ChatGPT share 6ae89b85) + материалы `/Users/solominaag/КОРПОРАЦИЯ` |
| `config/company.json` | Новый; направления — по решению владельца 26.10.2026 (`10_corporation_repo/knowledge/portfolio-owner-decision-2026-10-26.md`) |
| `org/agents.json` | Новый реестр ролей Blueprint v1; форма контракта наследует `10_corporation_repo/org/agents.json` (inputs/outputs/allowed_tools/data_classes/budget/independent_reviewer) |
| `src/board.mjs` | Новый код; продолжает линию `10_corporation_repo/src/workboard.mjs` (приёмка по sha256, защита от устаревшего решения) + добавляет протокол задач и human approval. Не копия: новая схема, новые правила, новые статусы |
| `tests/board.test.mjs` | Новый |
| `config/model-router.json`, `schemas/task.schema.json`, `blueprints/*`, `AGENTS.md`, `CODEX_MASTER_INSTRUCTION.md` | Новые, по содержанию чата-источника |

Исходные материалы в `/Users/solominaag/КОРПОРАЦИЯ` не изменялись. Цифры референс-компаний и названия моделей из чата-источника не перепроверялись.

## Решения владельца через approval-бот

| Дата | Запрос | Решение | Применено |
|---|---|---|---|
| 05.11.2026 | `2dd9ae47` — P0: бюджет и порядок MVP | «Утверждаю оба пункта»: инфраструктура ~$50–80/мес + AI API потолок $15/день; порядок P0 foundation → P1 редакция «Сила малых групп» → P2 Control Tower → P3 Sales → P4 Codex+Claude | `docs/ROADMAP.md` |
| 06.11.2026 | `feb7741b` — K-13: карта направлений | «Слияние: 7 направлений»: 5 контуров blueprint + Обучение ИИ + BrandFactory; R&D/Startup Lab — направление (kill-критерий обязателен) | `config/company.json` 1.1, `blueprints/company.yaml` 0.3 |
