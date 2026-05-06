"""Quiz agent for simple textbook-grounded practice questions."""

import json
import re
from typing import Any

from backend.services.llm_client import LLMClient, LLMClientError


class QuizAgent:
    """Generates short practice questions from retrieved context."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate(self, question: str, sources: list[dict[str, Any]]) -> list[str]:
        return [item["question"] for item in self.generate_items(question, sources)]

    def generate_items(self, question: str, sources: list[dict[str, Any]]) -> list[dict[str, str]]:
        if not sources:
            return [
                {
                    "question": "There is not enough textbook context to create quiz questions.",
                    "expected_answer": "Not enough textbook context.",
                    "weak_area": "textbook context",
                },
            ]

        if self.llm_client.is_mock:
            return self._mock_items(sources)

        system_prompt = (
            "You create primary-school quiz questions. Use only the provided textbook "
            "context. Keep questions simple. Return only a JSON array of exactly 3 "
            "objects. Each object must have question, expected_answer, and weak_area. "
            "Do not include explanations or markdown."
        )
        prompt = (
            f"Student question:\n{question}\n\n"
            f"Textbook context:\n{self._format_sources(sources)}\n\n"
            "Create 3 simple auto-gradable quiz questions with short expected answers."
        )
        try:
            response = self.llm_client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=300,
            )
        except LLMClientError:
            return self._mock_items(sources)

        return self._parse_items(response, sources)

    def _parse_items(self, response: str, sources: list[dict[str, Any]]) -> list[dict[str, str]]:
        response = response.strip()

        try:
            parsed = json.loads(self._extract_json_array(response))
        except (TypeError, ValueError):
            parsed = []

        items = []

        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    question = str(item.get("question", "")).strip()
                    expected_answer = str(item.get("expected_answer", "")).strip()
                    weak_area = str(item.get("weak_area", "")).strip()

                    if question:
                        items.append(
                            {
                                "question": question,
                                "expected_answer": expected_answer or self._source_answer(sources),
                                "weak_area": weak_area or self._source_weak_area(sources),
                            }
                        )
                elif isinstance(item, str) and item.strip():
                    items.append(
                        {
                            "question": item.strip(),
                            "expected_answer": self._source_answer(sources),
                            "weak_area": self._source_weak_area(sources),
                        }
                    )

        if not items:
            items = [
                {
                    "question": question,
                    "expected_answer": self._source_answer(sources),
                    "weak_area": self._source_weak_area(sources),
                }
                for question in self._parse_questions(response)
            ]

        return (items or self._mock_items(sources))[:3]

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

    def _mock_items(self, sources: list[dict[str, Any]]) -> list[dict[str, str]]:
        context = str(sources[0].get("text", "")).strip()

        if not context:
            return [
                {
                    "question": "There is not enough textbook context to create quiz questions.",
                    "expected_answer": "Not enough textbook context.",
                    "weak_area": "textbook context",
                }
            ]

        short_context = self._truncate(context, max_length=120)
        expected_answer = self._source_answer(sources)
        weak_area = self._source_weak_area(sources)
        return [
            {
                "question": "What is the main idea in the retrieved textbook context?",
                "expected_answer": expected_answer,
                "weak_area": weak_area,
            },
            {
                "question": f"What does this textbook line mean: {short_context}",
                "expected_answer": expected_answer,
                "weak_area": weak_area,
            },
            {
                "question": "Can you explain the answer in your own simple words?",
                "expected_answer": expected_answer,
                "weak_area": weak_area,
            },
        ]

    def _truncate(self, text: str, max_length: int = 500) -> str:
        if len(text) <= max_length:
            return text

        return f"{text[: max_length - 3]}..."

    def _source_answer(self, sources: list[dict[str, Any]]) -> str:
        text = str(sources[0].get("text", "")).strip()
        first_sentence = re.split(r"(?<=[.!?])\s+", text)[0].strip()
        return self._truncate(first_sentence or text, max_length=180)

    def _source_weak_area(self, sources: list[dict[str, Any]]) -> str:
        text = str(sources[0].get("text", "")).strip()
        words = [
            word.strip(".,?!:;()[]{}\"'").lower()
            for word in text.split()
            if len(word.strip(".,?!:;()[]{}\"'")) > 4
        ]
        return words[0] if words else "textbook concept"
