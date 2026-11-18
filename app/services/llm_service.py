"""LLM integration layer.

Supports three providers behind one interface (chosen via LLM_PROVIDER env var):
  - Google Gemini   (recommended: gemini-2.5-flash — fast, reliable native JSON mode)
  - OpenAI          (gpt-4o-mini fallback)
  - Anthropic       (claude-3-5-haiku-20241022 fallback)

All providers are called through their REST APIs with httpx (no vendor SDK
required) and are asked for STRICT JSON output, which is parsed and validated.
"""
import json
import re
import time
from typing import Any

import httpx

from app.config import settings


class LLMError(Exception):
    """Raised when the LLM call fails or returns unparseable output."""


class LLMResponse:
    def __init__(self, data: dict[str, Any], latency_ms: int, usage: dict[str, int]):
        self.data = data
        self.latency_ms = latency_ms
        self.usage = usage  # {"prompt_tokens": int, "completion_tokens": int}


def _extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from LLM output, tolerating markdown fences."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Last resort: grab the outermost {...} block.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise LLMError("LLM did not return valid JSON.")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMError("LLM returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise LLMError("LLM JSON output was not an object.")
    return parsed


def _retry(fn, attempts: int = 2, backoff: float = 1.5):
    """Retry transient LLM failures (rate limits / 5xx / timeouts / transient JSON glitches)."""
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
        except LLMError as exc:
            # Do not retry client configuration errors (e.g. missing API key)
            if "not configured" in str(exc):
                raise
            last_exc = exc
        if attempt < attempts - 1:
            time.sleep(backoff ** attempt)
    raise LLMError(f"LLM request failed after {attempts} attempts: {last_exc}")


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #

def _call_gemini(system_prompt: str, user_prompt: str) -> LLMResponse:
    api_key = settings.gemini_api_key
    if not api_key:
        raise LLMError("GEMINI_API_KEY is not configured.")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        # Native structured-output mode: model is constrained to valid JSON.
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.4,
            "maxOutputTokens": 4096,
        },
    }
    start = time.monotonic()
    response = httpx.post(
        url, json=payload, headers={"x-goog-api-key": api_key}, timeout=90
    )
    latency = int((time.monotonic() - start) * 1000)
    if response.status_code != 200:
        detail = response.text[:300]
        raise LLMError(f"Gemini API error {response.status_code}: {detail}")
    body = response.json()
    usage = {
        "prompt_tokens": body.get("usageMetadata", {}).get("promptTokenCount", 0),
        "completion_tokens": body.get("usageMetadata", {}).get("candidatesTokenCount", 0),
    }
    candidates = body.get("candidates", [])
    if not candidates:
        block = body.get("promptFeedback", {}).get("blockReason")
        raise LLMError(f"Gemini returned no candidates (blockReason={block}).")

    parts = candidates[0].get("content", {}).get("parts", [])
    # Filter out reasoning/thought blocks so only text content is parsed
    text = "".join(p.get("text", "") for p in parts if "text" in p and not p.get("thought"))
    if not text.strip():
        raise LLMError("Gemini returned empty text content.")
    return LLMResponse(_extract_json(text), latency, usage)


def _call_openai(system_prompt: str, user_prompt: str) -> LLMResponse:
    api_key = settings.openai_api_key
    if not api_key:
        raise LLMError("OPENAI_API_KEY is not configured.")
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
    }
    start = time.monotonic()
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=90,
    )
    latency = int((time.monotonic() - start) * 1000)
    if response.status_code != 200:
        raise LLMError(f"OpenAI API error {response.status_code}: {response.text[:300]}")
    body = response.json()
    usage_raw = body.get("usage", {})
    usage = {
        "prompt_tokens": usage_raw.get("prompt_tokens", 0),
        "completion_tokens": usage_raw.get("completion_tokens", 0),
    }
    text = body["choices"][0]["message"]["content"] or ""
    return LLMResponse(_extract_json(text), latency, usage)


def _call_anthropic(system_prompt: str, user_prompt: str) -> LLMResponse:
    api_key = settings.anthropic_api_key
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY is not configured.")
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 4096,
        "temperature": 0.4,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    start = time.monotonic()
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        json=payload,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        timeout=90,
    )
    latency = int((time.monotonic() - start) * 1000)
    if response.status_code != 200:
        raise LLMError(f"Anthropic API error {response.status_code}: {response.text[:300]}")
    body = response.json()
    usage = {
        "prompt_tokens": body.get("usage", {}).get("input_tokens", 0),
        "completion_tokens": body.get("usage", {}).get("output_tokens", 0),
    }
    text = "".join(
        block.get("text", "") for block in body.get("content", []) if block.get("type") == "text"
    )
    return LLMResponse(_extract_json(text), latency, usage)


_PROVIDERS = {
    "gemini": _call_gemini,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
}


def generate_json(system_prompt: str, user_prompt: str) -> LLMResponse:
    """Call the configured LLM provider and return validated JSON + metadata."""
    provider = _PROVIDERS[settings.llm_provider]
    return _retry(lambda: provider(system_prompt, user_prompt))
