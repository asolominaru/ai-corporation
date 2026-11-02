# Шлюз ИИ-корпорации (LiteLLM)

Единый API-шлюз для агентов дашборда «ИИ-Корпорация». Слушает `http://localhost:4000`.

## Настройка

1. Скопируйте `.env.example` в `.env`
2. Вставьте свои API-ключи (любой набор — работают только агенты с заполненными ключами)

## Запуск

```bash
./start.sh
```

## Маршрутизация агентов

| Алиас | Агент | Модель по умолчанию | Переменная ключа |
|---|---|---|---|
| `agent-ceo` | КОРД | moonshot/kimi-k2-0905-preview | `MOONSHOT_API_KEY` |
| `agent-scout` | СКАУТ | perplexity/sonar-pro | `PERPLEXITY_API_KEY` |
| `agent-researcher` | ИСКАТЕЛЬ | openai/gpt-5 | `OPENAI_API_KEY` |
| `agent-analyst` | ВЕСТА | anthropic/claude-sonnet-4-5 | `ANTHROPIC_API_KEY` |
| `agent-arch` | АРХИТЕКТОР | openai/gpt-5 | `OPENAI_API_KEY` |
| `agent-eng` | ИНЖЕНЕР | openai/gpt-5-mini | `OPENAI_API_KEY` |
| `agent-copy` | АВТОР | gemini/gemini-2.5-pro | `GEMINI_API_KEY` |
| `agent-edit` | РЕДАКТОР | anthropic/claude-haiku-4-5 | `ANTHROPIC_API_KEY` |
| `agent-qa` | РЕЦЕНЗЕНТ | deepseek/deepseek-reasoner | `DEEPSEEK_API_KEY` |
| `agent-rel` | РЕЛИЗ | openrouter/meta-llama/llama-4-maverick | `OPENROUTER_API_KEY` |

Модель любого агента можно заменить в `config.yaml` — LiteLLM поддерживает 100+
провайдеров (формат `провайдер/модель`), включая локальные через Ollama.
