"""Quiz agent for simple textbook-grounded practice questions."""

import json
import re
from typing import Any

from backend.services.llm_client import LLMClient


class QuizAgent:
    """Generates short practice questions from retrieved context."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate(self, question: str, sources: list[dict[str, Any]]) -> list[str]:
        if not sources:
            return [
                "There is not enough textbook context to create quiz questions.",
            ]

        if self.llm_client.is_mock:
            return self._mock_questions(sources)

        system_prompt = (
            "You create primary-school quiz questions. Use only the provided textbook "
            "context. Keep questions simple. If the context is insufficient, say so. "
            "Return only a JSON array of exactly 3 strings."
        )
        prompt = (
            f"Student question:\n{question}\n\n"
            f"Textbook context:\n{self._format_sources(sources)}\n\n"
            "Create 3 simple quiz questions."
        )
        response = self.llm_client.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=300,
        )

        return self._parse_questions(response)

    def _parse_questions(self, response: str) -> list[str]:
        response = response.strip()

        try:
            parsed = json.loads(self._extract_json_array(response))
            questions = [item.strip() for item in parsed if isinstance(item, str)]
        except (TypeError, ValueError):
            questions = [
                self._clean_question_line(line)
                for line in response.splitlines()
                if self._clean_question_line(line)
            ]

        questions = [question for question in questions if question]

        if not questions:
            return ["Could not create quiz questions from the available context."]

        return questions[:3]

    def _extract_json_array(self, response: str) -> str:
        match = re.search(r"\[[\s\S]*\]", response)
        return match.group(0) if match else response

    def _clean_question_line(self, line: str) -> str:
        cleaned = line.strip().strip("`").strip()

        if not cleaned or cleaned in {"[", "]"}:
            return ""

        cleaned = re.sub(r"^\s*[-*]?\s*\d+[\).\s-]*", "", cleaned)
        cleaned = cleaned.strip().strip(",").strip('"').strip("'").strip()

        if cleaned in {"[", "]"}:
            return ""

        return cleaned

    def _format_sources(self, sources: list[dict[str, Any]]) -> str:
        formatted_sources = []

        for index, source in enumerate(sources, start=1):
            metadata = source.get("metadata", {})
            filename = metadata.get("filename", "textbook")
            chunk_index = metadata.get("chunk_index", "unknown")
            text = source.get("text", "")
            formatted_sources.append(
                f"[Source {index}: {filename}, chunk {chunk_index}]\n{text}"
            )

        return "\n\n".join(formatted_sources)

    def _mock_questions(self, sources: list[dict[str, Any]]) -> list[str]:
        context = str(sources[0].get("text", "")).strip()

        if not context:
            return ["There is not enough textbook context to create quiz questions."]

        short_context = self._truncate(context, max_length=120)
        return [
            "What is the main idea in the retrieved textbook context?",
            f"What does this textbook line mean: {short_context}",
            "Can you explain the answer in your own simple words?",
        ]

    def _truncate(self, text: str, max_length: int = 500) -> str:
        if len(text) <= max_length:
            return text

        return f"{text[: max_length - 3]}..."
