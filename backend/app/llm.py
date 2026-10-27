"""OpenAI-compatible chat-completions client.

Works with OpenRouter, a local Ollama/vLLM server, LM Studio, or any other
provider exposing `/chat/completions`. The API key stays on the server; the
browser only ever learns whether the provider is configured and reachable.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

from .config import Settings
from .utils import utcnow

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    data: dict[str, Any]
    model: str
    latency_ms: int
    raw_text: str


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object in a model response, tolerating code fences."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[-1]
        if candidate.rstrip().endswith("```"):
            candidate = candidate.rstrip()[:-3]
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    parsed = json.loads(candidate[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model output is not a JSON object")
    return parsed


class LLMClient:
    COOLDOWN_SECONDS = 60

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self._transport = transport
        self.last_error: str | None = None
        self.last_error_at: datetime | None = None
        self.last_success_at: datetime | None = None
        self.last_latency_ms: int | None = None
        self.retry_after: datetime | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.settings.llm_enabled and self.settings.llm_configured)

    @property
    def degraded(self) -> bool:
        """True when the last provider attempt failed and no later success exists."""
        if self.last_error_at is None:
            return False
        if self.last_success_at is None:
            return True
        return self.last_error_at >= self.last_success_at

    @property
    def endpoint(self) -> str:
        return f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"

    def _record_error(self, message: str) -> None:
        self.last_error = message[:400]
        self.last_error_at = utcnow()
        self.retry_after = utcnow() + timedelta(seconds=self.COOLDOWN_SECONDS)
        logger.warning("LLM call failed: %s", self.last_error)

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/supportpilot-ai",
            "X-Title": "SupportPilot AI",
        }
        async with httpx.AsyncClient(transport=self._transport, timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(self.endpoint, headers=headers, json=payload)
        if response.status_code >= 400:
            detail = response.text.strip().replace("\n", " ")[:220]
            raise LLMError(f"provider returned HTTP {response.status_code}: {detail}")
        body = response.json()
        if not isinstance(body, dict) or not body.get("choices"):
            raise LLMError("provider response did not contain any choices")
        return body

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResult | None:
        """Run one JSON-mode completion. Returns None on any failure (caller falls back)."""
        if not self.enabled:
            return None
        # After a failure, stop hammering a dead provider; the Settings page can
        # still force a live check through `ping`.
        if self.retry_after is not None and utcnow() < self.retry_after:
            return None

        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.llm_temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.settings.llm_max_tokens,
            "response_format": {"type": "json_object"},
        }

        started = time.perf_counter()
        try:
            body = await self._post(payload)
            content = body["choices"][0]["message"].get("content") or ""
            if not content.strip():
                raise LLMError("provider returned an empty message")
            data = extract_json_object(content)
        except Exception as exc:  # noqa: BLE001 - provider failure must never break ticket creation
            self._record_error(str(exc) if isinstance(exc, LLMError) else f"{type(exc).__name__}: {exc}")
            return None

        latency_ms = int((time.perf_counter() - started) * 1000)
        self.last_success_at = utcnow()
        self.last_error = None
        self.last_error_at = None
        self.retry_after = None
        self.last_latency_ms = latency_ms
        return LLMResult(
            data=data,
            model=str(body.get("model") or self.settings.llm_model),
            latency_ms=latency_ms,
            raw_text=content,
        )

    async def ping(self) -> dict[str, Any]:
        """Cheap live connectivity check used by the Settings screen."""
        if not self.settings.llm_enabled:
            return {"ok": False, "detail": "LLM usage is disabled with LLM_ENABLED=false.", "latency_ms": None}
        if not self.settings.llm_configured:
            return {"ok": False, "detail": "No LLM_API_KEY configured; using the built-in analyst.", "latency_ms": None}

        started = time.perf_counter()
        try:
            body = await self._post(
                {
                    "model": self.settings.llm_model,
                    "messages": [{"role": "user", "content": "Reply with the single word OK."}],
                    "max_tokens": 8,
                    "temperature": 0,
                }
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.last_success_at = utcnow()
            self.last_error = None
            self.last_error_at = None
            self.retry_after = None
            self.last_latency_ms = latency_ms
            model = str(body.get("model") or self.settings.llm_model)
            return {"ok": True, "detail": f"Connected to {model}.", "latency_ms": latency_ms}
        except Exception as exc:  # noqa: BLE001
            detail = str(exc) if isinstance(exc, LLMError) else f"{type(exc).__name__}: {exc}"
            self._record_error(detail)
            return {"ok": False, "detail": self.last_error, "latency_ms": None}

    def status(self) -> dict[str, Any]:
        configured = self.settings.llm_configured
        active = bool(self.settings.llm_enabled and configured and not self.degraded)
        retry_in = None
        if self.retry_after is not None and self.retry_after > utcnow():
            retry_in = max(0, int((self.retry_after - utcnow()).total_seconds()))
        return {
            "enabled": self.settings.llm_enabled,
            "configured": configured,
            "degraded": self.degraded,
            "provider": self.settings.llm_provider,
            "model": self.settings.llm_model,
            "mode": "llm" if active else "fallback",
            "base_url_host": _host_only(self.settings.llm_base_url),
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "last_success_at": self.last_success_at,
            "last_latency_ms": self.last_latency_ms,
            "retry_in_seconds": retry_in,
        }


def _host_only(url: str) -> str:
    try:
        return httpx.URL(url).host or url
    except Exception:  # noqa: BLE001
        return url