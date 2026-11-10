"""Провайдеры LLM. Ключи — только из env процесса router'а (K-12:
клиент никогда не видит master credential). Без ключа провайдер
недоступен — fail closed, а не мок.

R-03: ключ уходит ТОЛЬКО на URL из серверного ALLOWED_BASE_URLS —
проверка выполняется непосредственно перед HTTP-запросом.
"""
import os
import time

import httpx

from .config import ALLOWED_BASE_URLS
from .models import Model

# provider → (env с ключом, base_url по умолчанию)
PROVIDERS = {
    "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1"),
    "anthropic": ("ANTHROPIC_API_KEY", "https://api.anthropic.com/v1"),
    "google": ("GOOGLE_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai"),
    "litellm": ("LITELLM_MASTER_KEY", None),  # base_url из endpoint_config, всё равно ∈ allowlist
}


class ProviderError(Exception):
    pass


class ProviderNotConfigured(ProviderError):
    """Нет ключа/endpoint — отказ до вызова, резерв снимается."""


class EndpointNotAllowed(ProviderError):
    """URL не из серверного allowlist — ключ никуда не отправляется (R-03)."""


def resolve_base_url(model: Model) -> str:
    provider = model.provider
    if provider not in PROVIDERS:
        raise ProviderNotConfigured(f"неизвестный провайдер: {provider}")
    default_base = PROVIDERS[provider][1]
    base = ((model.endpoint_config or {}).get("base_url") or default_base or "").rstrip("/")
    if not base:
        raise ProviderNotConfigured(f"провайдер {provider} без base_url")
    if base not in ALLOWED_BASE_URLS:
        raise EndpointNotAllowed(f"endpoint {base} не входит в серверный allowlist")
    return base


class ChatResult:
    def __init__(self, text, tokens_in, tokens_out, latency_ms):
        self.text = text
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.latency_ms = latency_ms


def chat(model: Model, messages: list[dict], max_tokens: int = 2000) -> ChatResult:
    provider = model.provider
    env_key = PROVIDERS.get(provider, (None, None))[0]
    base = resolve_base_url(model)  # allowlist — ДО любой сетевой активности
    api_key = os.getenv(env_key) if env_key else None
    if not api_key:
        raise ProviderNotConfigured(
            f"провайдер {provider} не сконфигурирован (нет {env_key})")

    started = time.monotonic()
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model.model_name, "messages": messages,
                      "max_tokens": max_tokens},
            )
    except httpx.HTTPError as e:
        raise ProviderError(f"сеть: {e}") from e
    latency_ms = int((time.monotonic() - started) * 1000)

    if resp.status_code != 200:
        raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    usage = data.get("usage") or {}
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    return ChatResult(
        text=text,
        tokens_in=int(usage.get("prompt_tokens") or 0),
        tokens_out=int(usage.get("completion_tokens") or 0),
        latency_ms=latency_ms,
    )
