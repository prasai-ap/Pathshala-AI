"""OpenAI-compatible LLM client for AMD Developer Cloud vLLM endpoints."""

import os
from functools import lru_cache
from typing import Any

import requests


DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"


class LLMClientError(RuntimeError):
    """Raised when a configured LLM endpoint cannot return a completion."""


class LLMClient:
    """Small wrapper around an OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
        self.timeout_seconds = timeout_seconds

    @property
    def is_mock(self) -> bool:
        return not self.base_url

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        """Return a single assistant response for a plain prompt."""
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})
        return self.chat(messages=messages, temperature=temperature, max_tokens=max_tokens)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        """Return assistant text from an OpenAI-compatible chat completion."""
        if not messages:
            raise ValueError("messages cannot be empty.")

        if self.is_mock:
            return self._mock_response(messages)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise LLMClientError("LLM endpoint timed out.") from exc
        except requests.HTTPError as exc:
            detail = self._truncate(response.text)
            raise LLMClientError(
                f"LLM endpoint returned HTTP {response.status_code}: {detail}"
            ) from exc
        except requests.RequestException as exc:
            raise LLMClientError(f"LLM endpoint request failed: {exc}") from exc

        try:
            data = response.json()
            return self._extract_message_content(data)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMClientError("LLM endpoint returned an unexpected response.") from exc

    def _extract_message_content(self, data: dict[str, Any]) -> str:
        content = data["choices"][0]["message"]["content"]

        if not isinstance(content, str):
            raise TypeError("message content must be a string.")

        return content

    def _mock_response(self, messages: list[dict[str, str]]) -> str:
        latest_user_message = next(
            (
                message.get("content", "")
                for message in reversed(messages)
                if message.get("role") == "user"
            ),
            "",
        )
        preview = self._truncate(latest_user_message, max_length=160)
        return (
            "[mock llm] LLM_BASE_URL is not configured. "
            f"Received prompt: {preview}"
        )

    def _truncate(self, text: str, max_length: int = 500) -> str:
        if len(text) <= max_length:
            return text

        return f"{text[: max_length - 3]}..."


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient()
