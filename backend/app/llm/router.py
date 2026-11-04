"""Stage 3: Anti-429 Multi-Provider LLM Router with token buckets + deterministic fallback."""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import httpx

from app.config import settings


@dataclass
class ProviderSlot:
    name: str
    model: str
    api_key: str
    rpm: int = 60
    rpd: int = 1000
    _minute_count: int = 0
    _minute_start: float = field(default_factory=time.time)
    _day_count: int = 0
    _day_start: float = field(default_factory=time.time)
    cooldown_until: float = 0.0
    failures: int = 0

    def available(self) -> bool:
        now = time.time()
        if now - self._minute_start >= 60:
            self._minute_start = now
            self._minute_count = 0
        if now - self._day_start >= 86400:
            self._day_start = now
            self._day_count = 0
        if now < self.cooldown_until:
            return False
        return self._minute_count < self.rpm and self._day_count < self.rpd

    def reserve(self) -> None:
        self._minute_count += 1
        self._day_count += 1


class LLMRouter:
    """Rotates across provider key slots; trips cooldown circuit breaker on HTTP 429."""

    def __init__(self) -> None:
        s = settings()
        self.slots: List[ProviderSlot] = []
        self._build(s)

    def _build(self, s: dict) -> None:
        def add(keys: List[str], name: str, model: str, rpm: int, rpd: int) -> None:
            for k in keys:
                self.slots.append(ProviderSlot(name=name, model=model, api_key=k, rpm=rpm, rpd=rpd))

        add(s["groq_api_keys"], "groq", "openai/gpt-oss-120b", 60, 1000)
        add(s["groq_api_keys"], "groq", "qwen/qwen3.8-27b", 60, 1000)
        add(s["gemini_api_keys"], "gemini", "gemini-2.5-flash", 60, 1000)
        add(s["openrouter_api_keys"], "openrouter", "nvidia/nemotron-3.5-lightning:free", 60, 1000)
        add(s["openrouter_api_keys"], "openrouter", "thinkingmachines/inkling:free", 60, 1000)
        add(s["mistral_api_keys"], "mistral", "mistral-small-latest", 60, 1000)
        add(s["xai_api_keys"], "xai", "grok-2-latest", 60, 1000)

    def pick(self) -> Optional[ProviderSlot]:
        candidates = [s for s in self.slots if s.available()]
        if not candidates:
            return None
        random.shuffle(candidates)
        return candidates[0]

    def mark_429(self, slot: ProviderSlot, retry_after: Optional[float] = None) -> None:
        slot.failures += 1
        slot.cooldown_until = time.time() + (retry_after or 60.0)

    def mark_success(self, slot: ProviderSlot) -> None:
        slot.reserve()
        slot.failures = 0
        slot.cooldown_until = 0.0

    def has_external_keys(self) -> bool:
        return len(self.slots) > 0

    # ------------------------------------------------------------------ #
    # Provider calls
    # ------------------------------------------------------------------ #
    def _call_provider(self, slot: ProviderSlot, system_prompt: str, user_prompt: str) -> Optional[dict]:
        if slot.name == "groq":
            return self._call_groq(slot, system_prompt, user_prompt)
        if slot.name == "openrouter":
            return self._call_openrouter(slot, system_prompt, user_prompt)
        if slot.name == "gemini":
            return self._call_gemini(slot, system_prompt, user_prompt)
        if slot.name == "mistral":
            return self._call_mistral(slot, system_prompt, user_prompt)
        if slot.name == "xai":
            return self._call_xai(slot, system_prompt, user_prompt)
        return None

    def _post_json(self, url: str, headers: dict, payload: dict, timeout: float = 40.0) -> dict:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 429:
                raise httpx.HTTPStatusError("429", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp.json()

    def _call_groq(self, slot: ProviderSlot, system_prompt: str, user_prompt: str) -> Optional[dict]:
        payload = {
            "model": slot.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        data = self._post_json(
            "https://api.groq.com/openai/v1/chat/completions",
            {"Authorization": f"Bearer {slot.api_key}", "Content-Type": "application/json"},
            payload,
        )
        content = data["choices"][0]["message"]["content"]
        return self._parse_json(content)

    def _call_openrouter(self, slot: ProviderSlot, system_prompt: str, user_prompt: str) -> Optional[dict]:
        payload = {
            "model": slot.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }
        data = self._post_json(
            "https://openrouter.ai/api/v1/chat/completions",
            {"Authorization": f"Bearer {slot.api_key}", "Content-Type": "application/json"},
            payload,
        )
        content = data["choices"][0]["message"]["content"]
        return self._parse_json(content)

    def _call_gemini(self, slot: ProviderSlot, system_prompt: str, user_prompt: str) -> Optional[dict]:
        payload = {
            "contents": [{"parts": [{"text": system_prompt + "\n\n" + user_prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
        }
        data = self._post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{slot.model}:generateContent?key={slot.api_key}",
            {"Content-Type": "application/json"},
            payload,
        )
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        content = parts[0].get("text", "") if parts else ""
        return self._parse_json(content)

    def _call_mistral(self, slot: ProviderSlot, system_prompt: str, user_prompt: str) -> Optional[dict]:
        payload = {
            "model": slot.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        data = self._post_json(
            "https://api.mistral.ai/v1/chat/completions",
            {"Authorization": f"Bearer {slot.api_key}", "Content-Type": "application/json"},
            payload,
        )
        content = data["choices"][0]["message"]["content"]
        return self._parse_json(content)

    def _call_xai(self, slot: ProviderSlot, system_prompt: str, user_prompt: str) -> Optional[dict]:
        payload = {
            "model": slot.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }
        data = self._post_json(
            "https://api.x.ai/v1/chat/completions",
            {"Authorization": f"Bearer {slot.api_key}", "Content-Type": "application/json"},
            payload,
        )
        content = data["choices"][0]["message"]["content"]
        return self._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> Optional[dict]:
        try:
            import json
            return json.loads(content)
        except Exception:
            # try to salvage a JSON object embedded in text
            import re, json as _json
            m = re.search(r"\{.*\}", content, re.S)
            if m:
                try:
                    return _json.loads(m.group(0))
                except Exception:
                    return None
            return None

    # ------------------------------------------------------------------ #
    # Main entry: external generation with deterministic fallback
    # ------------------------------------------------------------------ #
    def complete_json(self, system_prompt: str, user_prompt: str) -> Optional[dict]:
        if not self.has_external_keys():
            return None
        last_error = ""
        attempts = 0
        max_attempts = len(self.slots) + 3
        while attempts < max_attempts:
            slot = self.pick()
            if slot is None:
                break
            attempts += 1
            try:
                result = self._call_provider(slot, system_prompt, user_prompt)
                if result is not None:
                    self.mark_success(slot)
                    return result
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    retry = exc.response.headers.get("Retry-After")
                    delay = float(retry) if retry else 60.0
                    self.mark_429(slot, delay)
                    last_error = f"{slot.name} 429"
                    continue
                self.mark_429(slot, 60.0)
                last_error = f"{slot.name} {exc.response.status_code}"
                continue
            except Exception as exc:  # noqa: BLE001
                self.mark_429(slot, 60.0)
                last_error = f"{slot.name} {type(exc).__name__}"
                continue
        return None
