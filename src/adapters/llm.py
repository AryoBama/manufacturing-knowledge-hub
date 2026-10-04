from abc import ABC, abstractmethod
import os
import json
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """
    Standard interface for all LLM backend adapters.
    Each adapter encapsulates provider-specific protocols, endpoints, authentication, and payload formats.
    """

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> str:
        """Executes completion against the provider and returns text or serialized JSON string."""
        pass


class DeepSeekAdapter(LLMAdapter):
    """Adapter for DeepSeek API (deepseek-chat V3 flash tier / deepseek-reasoner R1)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        raw_model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        if raw_model in ("deepseek-flash", "flash", "chat"):
            raw_model = "deepseek-chat"
        self.model = raw_model
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
        self.timeout = timeout if timeout is not None else float(os.getenv("LLM_TIMEOUT", "18.0"))

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(self.base_url, headers=headers, json=payload)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]


class GeminiAdapter(LLMAdapter):
    """Adapter for Google Gemini API (gemini-1.5-flash, gemini-2.0-flash, gemini-1.5-pro)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        raw_model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        if raw_model in ("gemini-1.5-flash", "gemini-2.5-flash", "flash", "gemini-flash"):
            raw_model = "gemini-3.8-flash"
        self.model = raw_model
        self.base_url = base_url or os.getenv("GEMINI_BASE_URL", "") or f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.timeout = timeout if timeout is not None else float(os.getenv("LLM_TIMEOUT", "18.0"))

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        payload: dict = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }

        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(3):
                res = client.post(self.base_url, headers=headers, json=payload)
                if res.status_code in (503, 429) and attempt < 2:
                    import time
                    time.sleep(1.2 * (attempt + 1))
                    continue
                if res.is_error:
                    if res.status_code == 429:
                        logger.warning("Gemini API rate limit exceeded (429 Quota exhausted). Falling back.")
                    else:
                        logger.error("Gemini API error (%s): %s", res.status_code, res.text[:200])
                    res.raise_for_status()
                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("Gemini API returned no candidates.")
                return candidates[0]["content"]["parts"][0]["text"]



class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI API (gpt-4o-mini, gpt-4o)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
        self.timeout = timeout if timeout is not None else float(os.getenv("LLM_TIMEOUT", "18.0"))

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(self.base_url, headers=headers, json=payload)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]


class OfflineMockAdapter(LLMAdapter):
    """Deterministic offline adapter for unit testing and local sandboxes."""

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> str:
        if json_mode:
            return json.dumps({
                "intent": "general_information",
                "confidence": "LOW",
                "reason_code": "offline_mock",
            })
        return "Deterministic offline synthesis response."


def _load_dotenv_if_present() -> None:
    """Zero-dependency .env loader for local development environments."""
    from pathlib import Path
    root_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if root_env.exists():
        try:
            with open(root_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


def get_llm_adapter(provider: Optional[str] = None) -> LLMAdapter:
    """
    Factory creating the appropriate LLM adapter based on environment configuration.
    Defaults to OfflineMockAdapter if OFFLINE_MODE=true or no credentials are configured.
    """
    _load_dotenv_if_present()
    if os.getenv("OFFLINE_MODE", "false").lower() == "true":
        return OfflineMockAdapter()

    choice = (provider or os.getenv("LLM_PROVIDER", "")).lower()

    if choice == "deepseek" or (not choice and os.getenv("DEEPSEEK_API_KEY")):
        if os.getenv("DEEPSEEK_API_KEY"):
            return DeepSeekAdapter()
    elif choice == "gemini" or (not choice and os.getenv("GEMINI_API_KEY")):
        if os.getenv("GEMINI_API_KEY"):
            return GeminiAdapter()
    elif choice == "openai" or (not choice and os.getenv("OPENAI_API_KEY")):
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIAdapter()

    return OfflineMockAdapter()
