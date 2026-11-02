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
