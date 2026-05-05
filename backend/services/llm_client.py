"""
LLM client - OpenAI-compatible wrapper for AMD Developer Cloud vLLM endpoint

Environment variables used:
- LLM_BASE_URL (e.g. http://YOUR_AMD_CLOUD_IP:8000/v1)
- LLM_API_KEY
- LLM_MODEL

If LLM_BASE_URL is missing, the client returns a mock fallback response.
"""
from typing import Optional, List, Dict, Any
import os
import requests
import logging

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_MODEL") or "gpt-3.5-turbo"
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(self, prompt: Optional[str] = None, messages: Optional[List[Dict[str, Any]]] = None, max_tokens: int = 256, temperature: float = 0.0, **kwargs) -> Dict[str, Any]:
        """Generate a completion.

        - If `messages` is provided, uses the chat completions OpenAI-compatible path: `/chat/completions`.
        - Otherwise uses `/completions` with `prompt`.

        Returns the raw JSON response from the LLM endpoint. If `LLM_BASE_URL` is not configured a mock response is returned.
        """
        # Mock fallback when base_url missing
        if not self.base_url:
            logger.warning("LLM_BASE_URL not configured; returning mock response")
            text = None
            if prompt:
                text = prompt if len(prompt) < 200 else prompt[:200] + "..."
            elif messages:
                last = messages[-1].get("content") if messages and isinstance(messages, list) else ""
                text = last if len(str(last)) < 200 else str(last)[:200] + "..."
            else:
                text = "(mock) no prompt provided"

            return {
                "id": "mock-0",
                "object": "mock.completion",
                "model": self.model,
                "choices": [
                    {
                        "text": f"(mock) Response to: {text}",
                        "index": 0,
                        "finish_reason": "mock"
                    }
                ],
                "mock": True
            }

        try:
            if messages:
                url = self.base_url.rstrip("/") + "/chat/completions"
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            else:
                url = self.base_url.rstrip("/") + "/completions"
                payload = {
                    "model": self.model,
                    "prompt": prompt or "",
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

            headers = self._headers()
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)

            if resp.status_code >= 400:
                # Try to include server error message
                try:
                    err = resp.json()
                except Exception:
                    err = resp.text
                logger.error("LLM request failed: %s %s", resp.status_code, err)
                raise LLMError(f"LLM request failed ({resp.status_code}): {err}")

            try:
                return resp.json()
            except ValueError:
                # Non-JSON response
                text = resp.text
                logger.error("LLM returned non-JSON response: %s", text)
                raise LLMError("LLM returned non-JSON response")

        except requests.RequestException as e:
            logger.exception("Network error when calling LLM: %s", e)
            raise LLMError(f"Network error when calling LLM: {e}")


# Simple convenience function for quick use
def get_default_client(timeout: int = 30) -> LLMClient:
    return LLMClient(timeout=timeout)
