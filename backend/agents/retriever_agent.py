"""Retriever agent for textbook-grounded context search."""

from collections.abc import Callable
from typing import Any


class RetrieverAgent:
    """Retrieves relevant curriculum chunks for a student question."""

    def __init__(
        self,
        search_context: Callable[[str, int], list[dict[str, Any]]],
        default_limit: int = 5,
    ) -> None:
        self.search_context = search_context
        self.default_limit = default_limit

    def retrieve(self, question: str, limit: int | None = None) -> list[dict[str, Any]]:
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        return self.search_context(question, limit or self.default_limit)
