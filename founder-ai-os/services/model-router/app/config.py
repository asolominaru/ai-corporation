import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("MODEL_ROUTER_DATABASE_URL", f"sqlite:///{BASE_DIR}/dev.db")

# Лимиты расходов. ВАЖНО: дневной потолок $15 × 30 дней = $450 — это НЕ
# месячный лимит $280 из утверждённой сметы. Оба лимита применяются одновременно,
# месячный — связующий (дешевле). Значения — только из env в prod.
DAILY_CAP_USD = float(os.getenv("AI_DAILY_CAP_USD", "15"))
MONTHLY_CAP_USD = float(os.getenv("AI_MONTHLY_CAP_USD", "280"))

# Ключи провайдеров — только из env, никогда из кода/клиентов.
# Формат: OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY / LITELLM_BASE_URL...

# R-03: серверный allowlist адресов провайдеров. Ключ уходит только на URL
# из этого списка — и при регистрации модели, и при вызове.
_ALLOWED_DEFAULT = {
    "https://api.openai.com/v1",
    "https://api.anthropic.com/v1",
    "https://generativelanguage.googleapis.com/v1beta/openai",
}
ALLOWED_BASE_URLS = _ALLOWED_DEFAULT | {
    u.strip().rstrip("/")
    for u in os.getenv("ROUTER_ALLOWED_BASE_URLS", "").split(",") if u.strip()
}
