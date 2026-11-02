#!/bin/bash
# Запуск шлюза ИИ-корпорации на http://localhost:4000
cd "$(dirname "$0")"
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
exec ./venv/bin/litellm --config config.yaml --port 4000
