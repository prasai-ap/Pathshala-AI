"""Quiz agent for simple textbook-grounded practice questions."""

import json
import re
from typing import Any

from backend.services.llm_client import LLMClient, LLMClientError


class QuizAgent:
    """Generates short practice questions from retrieved context."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate(
        self,
        question: str,
        sources: list[dict[str, Any]],
        target_language: str = "Nepali",
    ) -> list[str]:
        return [
            item["question"]
            for item in self.generate_items(
                question,
                sources,
                target_language=target_language,
            )
        ]

    def generate_items(
        self,
        question: str,
        sources: list[dict[str, Any]],
        target_language: str = "Nepali",
    ) -> list[dict[str, str]]:
        if not sources:
            return [
                {
                    "question": "प्रश्न बनाउन पर्याप्त पाठ्यपुस्तक सन्दर्भ छैन।",
                    "expected_answer": "पर्याप्त पाठ्यपुस्तक सन्दर्भ छैन।",
                    "weak_area": "textbook context",
                },
            ]

        if self.llm_client.is_mock:
            return self._mock_items(sources, target_language=target_language)

        language_instruction = self._language_instruction(target_language)
        system_prompt = (
            "You create primary-school quiz questions. Use only the provided textbook "
            "context. Keep questions simple. Return only a JSON array of exactly 3 "
            "objects. Each object must have question, expected_answer, and weak_area. "
            f"{language_instruction} Do not include explanations or markdown."
        )
        prompt = (
            f"Student question:\n{question}\n\n"
            f"Textbook context:\n{self._format_sources(sources)}\n\n"
            "Create 3 simple auto-gradable quiz questions with short expected answers. "
            f"{language_instruction}"
        )
        try:
            response = self.llm_client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=300,
            )
        except LLMClientError:
            return self._mock_items(sources, target_language=target_language)

        parsed_items = self._parse_items(response, sources)

        if self._wants_nepali(target_language) and not self._items_are_nepali(parsed_items):
            return self._mock_items(sources, target_language=target_language)

        return parsed_items

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

    def _mock_items(
        self,
        sources: list[dict[str, Any]],
        target_language: str = "Nepali",
    ) -> list[dict[str, str]]:
        context = str(sources[0].get("text", "")).strip()

        if not context:
            return [
                {
                    "question": "प्रश्न बनाउन पर्याप्त पाठ्यपुस्तक सन्दर्भ छैन।",
                    "expected_answer": "पर्याप्त पाठ्यपुस्तक सन्दर्भ छैन।",
                    "weak_area": "textbook context",
                }
            ]

        short_context = self._truncate(context, max_length=120)
        expected_answer = self._source_answer(sources)
        weak_area = self._source_weak_area(sources)

        if self._wants_nepali(target_language):
            return [
                {
                    "question": "प्राप्त पाठ्यपुस्तक सन्दर्भको मुख्य कुरा के हो?",
                    "expected_answer": expected_answer,
                    "weak_area": weak_area,
                },
                {
                    "question": f"यो पाठ्यपुस्तकको वाक्यले के बुझाउँछ: {short_context}",
                    "expected_answer": expected_answer,
                    "weak_area": weak_area,
                },
                {
                    "question": "यस उत्तरलाई आफ्नै सरल शब्दमा कसरी भन्न सकिन्छ?",
                    "expected_answer": expected_answer,
                    "weak_area": weak_area,
                },
            ]

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

    def _language_instruction(self, target_language: str) -> str:
        if self._wants_nepali(target_language):
            return (
                "Write question, expected_answer, and weak_area in Nepali Devanagari. "
                "Do not translate Nepali textbook terms into English. Do not use English "
                "sentences."
            )

        return f"Write the quiz in {target_language}."

    def _wants_nepali(self, target_language: str) -> bool:
        return target_language.strip().lower().startswith("nepali")

    def _items_are_nepali(self, items: list[dict[str, str]]) -> bool:
        question_text = " ".join(item.get("question", "") for item in items)
        devanagari_count = sum(1 for character in question_text if "\u0900" <= character <= "\u097f")
        latin_count = sum(1 for character in question_text if character.isascii() and character.isalpha())
        return devanagari_count >= 10 and latin_count <= 20
