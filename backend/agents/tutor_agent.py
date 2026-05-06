"""Tutor agent for simple bilingual, textbook-grounded explanations."""

from typing import Any

from backend.services.llm_client import LLMClient


class TutorAgent:
    """Generates simple English and Nepali explanations from retrieved context."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def answer_english(self, question: str, sources: list[dict[str, Any]]) -> str:
        return self._answer(question=question, sources=sources, language="English")

    def answer_nepali(self, question: str, sources: list[dict[str, Any]]) -> str:
        return self._answer(question=question, sources=sources, language="Nepali")

    def _answer(self, question: str, sources: list[dict[str, Any]], language: str) -> str:
        if not sources:
            return (
                "I do not have enough textbook context to answer this question."
                if language == "English"
                else "यो प्रश्नको उत्तर दिन पर्याप्त पाठ्यपुस्तक सन्दर्भ छैन।"
            )

        if self.llm_client.is_mock:
            return self._mock_answer(sources=sources, language=language)

        system_prompt = (
            "You are a primary-school tutor. Use only the provided textbook context. "
            "Keep the explanation simple and short. If the context is insufficient, "
            "say that you do not have enough textbook context instead of guessing."
        )
        prompt = (
            f"Answer in {language}.\n\n"
            f"Student question:\n{question}\n\n"
            f"Textbook context:\n{self._format_sources(sources)}"
        )

        return self.llm_client.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=450,
        )

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

    def _mock_answer(self, sources: list[dict[str, Any]], language: str) -> str:
        context = str(sources[0].get("text", "")).strip()

        if not context:
            return (
                "I do not have enough textbook context to answer this question."
                if language == "English"
                else "यो प्रश्नको उत्तर दिन पर्याप्त पाठ्यपुस्तक सन्दर्भ छैन।"
            )

        short_context = self._truncate(context)

        if language == "English":
            return (
                "Based on the textbook context, here is the simple explanation: "
                f"{short_context}"
            )

        return f"पाठ्यपुस्तक सन्दर्भ अनुसार सरल व्याख्या: {short_context}"

    def _truncate(self, text: str, max_length: int = 500) -> str:
        if len(text) <= max_length:
            return text

        return f"{text[: max_length - 3]}..."
