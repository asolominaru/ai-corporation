# КОРПОРАЦИЯ — инструкции для Copilot

Монорепозиторий мультиагентной ИИ-системы («ИИ-Корпорация»): виртуальная компания
из 10 LLM-агентов в 6 отделах, управляемая владельцем. Рабочий язык — русский,
код и идентификаторы — на английском, комментарии и документация — на русском.

## Структура

| Папка | Что это | Стек |
|---|---|---|
| `app/` | Дашборд «Центр управления» | React 18 + TypeScript + Vite + Tailwind + shadcn/ui |
| `litellm-server/` | Шлюз к LLM-провайдерам | LiteLLM proxy, порт 4000, `config.yaml` |
| `approval-bot/` | Согласование решений через Telegram | Python 3.12, без фреймворков, append-only `approvals.jsonl` с hash-chain |
| `founder-ai-os/` | Founder AI OS — оргструктура, blueprints, workflows | Node.js (ESM, `.mjs`), JSON-схемы, YAML |
| `spain-vpn/` | Инфраструктура Spain-узла (VLESS/Xray) | Shell, конфиги Xray/Amnezia |

## Жёсткие правила

- **Секреты**: `.env` никогда не коммитится и не читается в код напрямую
  (только через `set -a; source .env` в shell или явную загрузку). Никогда
  не генерируй код, выводящий токены/ключи в лог.
- **approval-bot**: `approvals.jsonl` — append-only; записи не изменяются и не
  удаляются, только добавляются с hash-chain. Тесты (`test_approvals.py`)
  офлайн: сеть и `.env` не используются, `call()` подменяется заглушкой.
- **Аудит**: любые решения, требующие согласования владельца, идут через
  approval-bot с кнопками действий — не предлагай обходных путей.
- **app/**: компоненты — shadcn/ui из `app/src/components/ui`, стили — только
  Tailwind-классы, без inline-style и отдельных CSS-файлов под компоненты.
- **founder-ai-os**: Node ESM (`import`, не `require`); тесты — `node --test`.
- Не переименовывай и не перемещай файлы без явной просьбы; нумерованные
  префиксы папок (`00_`, `01_`, `10_`) — часть навигационной системы.

## Команды

- Дашборд: `cd app && npm run dev` (порт 5173), `npm run build`, `npm run lint`
- Шлюз: `litellm-server/start.sh` → http://localhost:4000
- Тесты approval-bot: `python approval-bot/test_approvals.py`
- Тесты founder-ai-os: `cd founder-ai-os && node --test tests/`

## Архитектурный контекст

Оргструктура агентов (КОРД, СКАУТ, ИСКАТЕЛЬ, ВЕСТА, АРХИТЕКТОР, ИНЖЕНЕР, АВТОР,
РЕДАКТОР, РЕЦЕНЗЕНТ, РЕЛИЗ) описана в корневом `README.md`. Каждый агент
привязан к модели через LiteLLM-алиасы в `litellm-server/config.yaml`.
Целевая архитектура аудита и кэширования — в `founder-ai-os/docs/`.
