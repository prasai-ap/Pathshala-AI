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

        if language == "Nepali":
            system_prompt = (
                "You are a primary-school tutor. Use only the provided textbook context. "
                "Write the answer in Nepali using Devanagari script only. Do not write "
                "English sentences. Keep the explanation simple and short. If the context "
                "is insufficient, say that there is not enough textbook context in Nepali."
            )
            prompt = (
                "नेपाली भाषामा मात्र उत्तर दिनुहोस्। अंग्रेजी वाक्य नलेख्नुहोस्।\n\n"
                f"विद्यार्थीको प्रश्न:\n{question}\n\n"
                f"पाठ्यपुस्तक सन्दर्भ:\n{self._format_sources(sources)}"
            )
        else:
            system_prompt = (
                "You are a primary-school tutor. Use only the provided textbook context. "
                "Write the answer in simple English. Keep the explanation short. If the "
                "context is insufficient, say that you do not have enough textbook context."
            )
            prompt = (
                f"Student question:\n{question}\n\n"
                f"Textbook context:\n{self._format_sources(sources)}"
            )

        answer = self.llm_client.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=450,
        )

        if language == "Nepali":
            answer = self._remove_source_lines(answer)

            if not self._is_valid_nepali_answer(answer):
                answer = self._retry_nepali_answer(question=question, sources=sources, draft=answer)

            if not self._is_valid_nepali_answer(answer):
                return self._fallback_nepali_answer(question=question, sources=sources)

        return answer

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

        return (
            "माफ गर्नुहोस्, mock mode मा नेपाली अनुवाद उपलब्ध छैन। "
            "तर उत्तर पाठ्यपुस्तक सन्दर्भमा आधारित छ।"
        )

    def _truncate(self, text: str, max_length: int = 500) -> str:
        if len(text) <= max_length:
            return text

        return f"{text[: max_length - 3]}..."

    def _is_valid_nepali_answer(self, text: str) -> bool:
        devanagari_count = sum(1 for character in text if "\u0900" <= character <= "\u097f")
        latin_count = sum(1 for character in text if character.isascii() and character.isalpha())

        if devanagari_count < 20:
            return False

        if latin_count > 12:
            return False

        forbidden_markers = ["source", "student question", "textbook context", "external"]
        return not any(marker in text.lower() for marker in forbidden_markers)

    def _retry_nepali_answer(
        self,
        question: str,
        sources: list[dict[str, Any]],
        draft: str,
    ) -> str:
        system_prompt = (
            "You are a Nepali translator and primary-school tutor. Rewrite the answer "
            "entirely in Nepali Devanagari script. Do not include English words, source "
            "citations, labels, markdown, or headings. Use only the textbook context."
        )
        prompt = (
            "तलको उत्तरलाई पूर्ण रूपमा नेपाली देवनागरीमा फेरि लेख्नुहोस्। "
            "अंग्रेजी शब्द वा स्रोत उल्लेख नराख्नुहोस्।\n\n"
            f"प्रश्न:\n{question}\n\n"
            f"मस्यौदा उत्तर:\n{draft}\n\n"
            f"पाठ्यपुस्तक सन्दर्भ:\n{self._format_sources(sources)}"
        )

        retried = self.llm_client.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=350,
        )
        return self._remove_source_lines(retried)

    def _remove_source_lines(self, text: str) -> str:
        cleaned_lines = []

        for line in text.splitlines():
            lowered = line.lower()

            if "source" in lowered or "बाहरी स्रोत" in line or "स्रोत:" in line:
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def _fallback_nepali_answer(
        self,
        question: str,
        sources: list[dict[str, Any]],
    ) -> str:
        topic_text = f"{question} {self._combined_source_text(sources)}".lower()
        concept_answer = self._known_nepali_concept_answer(topic_text)

        if concept_answer:
            return concept_answer

        return (
            "प्राप्त पाठ्यपुस्तक सन्दर्भ अनुसार यो विषय महत्त्वपूर्ण छ। "
            "यसलाई सजिलोसँग बुझ्न मुख्य शब्दहरू पढ्नुहोस्, उदाहरण हेर्नुहोस्, "
            "र आफ्नै शब्दमा छोटो उत्तर लेख्ने अभ्यास गर्नुहोस्।"
        )

    def _combined_source_text(self, sources: list[dict[str, Any]]) -> str:
        return " ".join(str(source.get("text", "")) for source in sources[:3])

    def _known_nepali_concept_answer(self, text: str) -> str | None:
        if "soil erosion" in text or "erosion" in text or "माटो कटान" in text:
            return (
                "माटो कटान भनेको हावा, पानी वा अन्य कारणले माटोको माथिल्लो मलिलो भाग "
                "बिस्तारै बगेर वा उडेर जानु हो। यसले खेतबारीको उर्वर शक्ति घटाउँछ। "
                "त्यसैले बिरुवा रोप्ने, घाँस जोगाउने र पानीको बहाव नियन्त्रण गर्ने काम "
                "माटो जोगाउन उपयोगी हुन्छ।"
            )

        if "oxygen" in text or "अक्सिजन" in text:
            return (
                "अक्सिजन एउटा ग्यास हो। जीवित प्राणीले सास फेर्दा अक्सिजन प्रयोग गर्छन्। "
                "कोषिकाले खाना तोडेर ऊर्जा बनाउन पनि अक्सिजनको मद्दत लिन्छ। "
                "त्यसैले अक्सिजन जीवनका लागि धेरै महत्त्वपूर्ण हुन्छ।"
            )

        if "photosynthesis" in text or "chlorophyll" in text or "प्रकाश संश्लेषण" in text:
            return (
                "प्रकाश संश्लेषण भनेको हरिया बिरुवाले घामको प्रकाश, पानी र कार्बन डाइअक्साइड "
                "प्रयोग गरेर आफ्नो खाना बनाउने प्रक्रिया हो। यो काम पातमा हुने हरियो पदार्थ "
                "क्लोरोफिलको मद्दतले हुन्छ। यस प्रक्रियामा अक्सिजन पनि निस्कन्छ।"
            )

        if "fraction" in text or "भिन्न" in text:
            return (
                "भिन्न भनेको कुनै पूर्ण वस्तुको भाग देखाउने संख्या हो। माथिको संख्या अंश हो, "
                "जसले कति भाग लिइयो भनेर देखाउँछ। तलको संख्या हर हो, जसले पूर्ण वस्तु कति "
                "बराबर भागमा बाँडिएको छ भनेर देखाउँछ।"
            )

        if "mitochondria" in text or "mitochondrion" in text:
            return (
                "माइटोकन्ड्रिया कोषिकाभित्र हुने सानो अंगक हो। यसको मुख्य काम खानाबाट ऊर्जा "
                "बनाउनु हो। त्यसैले यसलाई कोषिकाको ऊर्जा घर पनि भनिन्छ।"
            )

        if "chloroplast" in text or "plastid" in text:
            return (
                "क्लोरोप्लास्ट बिरुवाको कोषिकामा पाइने हरियो अंगक हो। यसमा क्लोरोफिल हुन्छ। "
                "क्लोरोफिलले घामको प्रकाश लिन मद्दत गर्छ र बिरुवाले खाना बनाउन सक्छ।"
            )

        if "cell" in text or "कोषिका" in text:
            return (
                "कोषिका जीवित वस्तुको सबैभन्दा सानो आधारभूत एकाइ हो। हाम्रो शरीर, बिरुवा "
                "र धेरै जीवहरू कोषिकाबाट बनेका हुन्छन्। कोषिकाले जीवनका आवश्यक कामहरू गर्छ।"
            )

        if "energy" in text or "ऊर्जा" in text:
            return (
                "ऊर्जा भनेको काम गर्न चाहिने शक्ति हो। जीवित प्राणीले खाना र सास फेर्ने "
                "प्रक्रियाबाट ऊर्जा पाउँछन्। कोषिकाले यही ऊर्जा प्रयोग गरेर जीवनका काम गर्छ।"
            )

        return None
