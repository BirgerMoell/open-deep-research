from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from .config import Settings


def _extract_message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                chunks.append(part.get("text", ""))
        return "\n".join(chunk for chunk in chunks if chunk)
    return ""


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.settings.llm_enabled

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("LLM is not configured")

        payload: Dict[str, object] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        body = json.dumps(payload).encode("utf-8")
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout_sec) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM request failed: {exc.code} {detail}") from exc

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        return _extract_message_text(message.get("content"))

    def generate_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, object]]:
        if not self.enabled:
            return None
        try:
            raw = self.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                json_mode=True,
            ).strip()
        except Exception:
            try:
                raw = self.chat(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt + "\n\nReturn JSON only."},
                    ],
                    json_mode=False,
                ).strip()
            except Exception:
                return None
        if not raw:
            return None
        cleaned = raw
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None
