"""Provider-agnostic LLM wrapper with JSON validation and retries."""

from __future__ import annotations

import json
import logging
import re
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Raised when the LLM call fails after retries."""


def _parse_model_spec(spec: str) -> tuple[str, str]:
    """Parse 'provider:model_id' into (provider, model_id)."""
    if ":" in spec:
        provider, model = spec.split(":", 1)
        return provider.strip().lower(), model.strip()
    # Default to openai if no provider prefix
    return "openai", spec.strip()


def _extract_json(text: str) -> str:
    """Pull JSON object/array out of markdown fences or surrounding prose."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        return fence.group(1).strip()
    # Find first { or [
    for i, ch in enumerate(text):
        if ch in "{[":
            return text[i:]
    return text


async def _call_openai(model: str, system: str, user: str, timeout: float) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError("OPENAI_API_KEY is not set")
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        if resp.status_code == 429:
            raise LLMError("OpenAI rate limit exceeded")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_anthropic(model: str, system: str, user: str, timeout: float) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise LLMError("ANTHROPIC_API_KEY is not set")
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 8192,
        "system": system + "\n\nRespond with valid JSON only.",
        "messages": [{"role": "user", "content": user}],
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        if resp.status_code == 429:
            raise LLMError("Anthropic rate limit exceeded")
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _call_google(model: str, system: str, user: str, timeout: float) -> str:
    settings = get_settings()
    if not settings.google_api_key:
        raise LLMError("GOOGLE_API_KEY is not set")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.google_api_key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": system + "\nRespond with valid JSON only."}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code == 429:
            raise LLMError("Google rate limit exceeded")
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def raw_completion(role: str, system: str, user: str) -> str:
    """
    Call the configured model for `role` ('generator' | 'qc').
    Returns raw text content.
    """
    settings = get_settings()
    spec = settings.generator_model if role == "generator" else settings.qc_model
    provider, model = _parse_model_spec(spec)
    timeout = float(settings.llm_timeout_seconds)

    # Guard: generator and QC must use different models
    gen_p, gen_m = _parse_model_spec(settings.generator_model)
    qc_p, qc_m = _parse_model_spec(settings.qc_model)
    if gen_p == qc_p and gen_m == qc_m:
        logger.warning(
            "GENERATOR_MODEL and QC_MODEL are identical (%s). "
            "QC independence is weakened.",
            settings.generator_model,
        )

    try:
        if provider == "openai":
            return await _call_openai(model, system, user, timeout)
        if provider == "anthropic":
            return await _call_anthropic(model, system, user, timeout)
        if provider in ("google", "gemini"):
            return await _call_google(model, system, user, timeout)
        raise LLMError(f"Unknown LLM provider: {provider}")
    except httpx.TimeoutException as e:
        raise LLMError(f"LLM timeout after {timeout}s") from e
    except httpx.HTTPStatusError as e:
        raise LLMError(f"LLM HTTP error {e.response.status_code}: {e.response.text[:300]}") from e


async def json_completion(
    role: str,
    system: str,
    user: str,
    schema: Type[T],
) -> T:
    """
    Call LLM and parse response into a pydantic model.
    Retries up to llm_max_retries times on malformed JSON / validation errors.
    """
    settings = get_settings()
    last_err: Exception | None = None
    feedback = ""

    for attempt in range(settings.llm_max_retries + 1):
        prompt = user
        if feedback:
            prompt = (
                f"{user}\n\nPREVIOUS OUTPUT WAS INVALID. Fix this error and "
                f"return ONLY valid JSON matching the schema:\n{feedback}"
            )
        try:
            raw = await raw_completion(role, system, prompt)
            cleaned = _extract_json(raw)
            data = json.loads(cleaned)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError, KeyError, IndexError) as e:
            last_err = e
            feedback = str(e)
            logger.warning("LLM JSON attempt %s failed: %s", attempt + 1, e)
        except LLMError:
            raise

    raise LLMError(f"LLM returned invalid JSON after retries: {last_err}")
