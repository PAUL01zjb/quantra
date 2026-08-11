"""OpenAI-compatible LLM client (shared by agent and extraction channels)."""

from __future__ import annotations

import json
import urllib.request

from quantra.config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def chat(self, messages: list[dict], model: str, temperature: float = 0.3) -> str:
        if not self.settings.api_key:
            raise RuntimeError("LLM API key not configured (QUANTRA_API_KEY)")
        payload = json.dumps(
            {"model": model, "messages": messages, "temperature": temperature}
        ).encode("utf-8")
        url = self.settings.api_base.rstrip("/") + "/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
