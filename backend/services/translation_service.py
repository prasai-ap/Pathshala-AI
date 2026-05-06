"""Optional Nepali language adaptation service."""

import logging
from functools import lru_cache
from typing import Any

import requests

from backend.services.config import AppConfig, get_config


LOGGER = logging.getLogger(__name__)


class TranslationService:
    """Adapts the grounded English tutor answer into simple Nepali."""

    def __init__(self, config: AppConfig | None = None, timeout_seconds: int = 45) -> None:
        self.config = config or get_config()
        self.timeout_seconds = timeout_seconds

    def to_nepali(
        self,
        question: str,
        english_answer: str,
        sources: list[dict[str, Any]],
    ) -> str:
        provider = self.config.translation_provider

        if provider == "gemini" and self.config.gemini_api_key:
            return self._with_provider_fallback(
                self._translate_with_gemini,
                question,
                english_answer,
                sources,
            )

        if provider == "openai" and self.config.openai_api_key:
            return self._with_provider_fallback(
                self._translate_with_openai,
                question,
                english_answer,
                sources,
            )

        LOGGER.info("Using mock Nepali adaptation because translation provider/key is missing.")
        return self._mock_nepali(question=question, english_answer=english_answer, sources=sources)

    def normalize_question(self, question: str) -> str:
        """Convert English, Nepali, or romanized Nepali into a clear English query."""
        cleaned_question = question.strip()

        if not cleaned_question:
            return cleaned_question

        provider = self.config.translation_provider

        if provider == "gemini" and self.config.gemini_api_key:
            try:
                normalized = self._normalize_with_gemini(cleaned_question)
                normalized = self._clean_normalized_question(normalized)

                if self._is_valid_normalized_question(normalized):
                    return normalized

                LOGGER.warning(
                    "Question normalization provider returned weak query: %s",
                    normalized,
                )
            except requests.RequestException as exc:
                LOGGER.warning("Question normalization provider failed: %s", exc)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                LOGGER.warning("Question normalization provider returned invalid response: %s", exc)

        return self._mock_normalize_question(cleaned_question)

    def _with_provider_fallback(
        self,
        provider_call,
        question: str,
        english_answer: str,
        sources: list[dict[str, Any]],
    ) -> str:
        try:
            translated = provider_call(question, english_answer)
        except requests.RequestException as exc:
            LOGGER.warning("Nepali adaptation provider failed: %s", exc)
            return self._mock_nepali(
                question=question,
                english_answer=english_answer,
                sources=sources,
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            LOGGER.warning("Nepali adaptation provider returned invalid response: %s", exc)
            return self._mock_nepali(
                question=question,
                english_answer=english_answer,
                sources=sources,
            )

        translated = self._remove_source_lines(translated)

        if self._is_valid_nepali(translated):
            return translated

        LOGGER.warning("Nepali adaptation provider returned weak Nepali; using mock fallback.")
        return self._mock_nepali(question=question, english_answer=english_answer, sources=sources)

    def _translate_with_gemini(self, question: str, english_answer: str) -> str:
        model = self.config.gemini_model
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent"
        )
        prompt = self._translation_prompt(question=question, english_answer=english_answer)
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 450,
            },
        }
        response = requests.post(
            endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.config.gemini_api_key,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _normalize_with_gemini(self, question: str) -> str:
        model = self.config.gemini_model
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": self._normalization_prompt(question),
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 80,
            },
        }
        response = requests.post(
            endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.config.gemini_api_key,
            },
            timeout=min(self.timeout_seconds, 20),
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _translate_with_openai(self, question: str, english_answer: str) -> str:
        payload = {
            "model": self.config.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You adapt English tutoring answers into natural Nepali for "
                        "primary-school students. Write only Nepali Devanagari. Do not "
                        "add source labels, markdown, or English sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": self._translation_prompt(
                        question=question,
                        english_answer=english_answer,
                    ),
                },
            ],
            "temperature": 0.1,
            "max_tokens": 450,
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.config.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _translation_prompt(self, question: str, english_answer: str) -> str:
        return (
            "Translate and simplify this grounded English tutoring answer into natural "
            "Nepali for a primary-school student in Nepal. Keep the same meaning. "
            "Use Nepali Devanagari only. Do not add new facts. Do not include source "
            "citations or headings.\n\n"
            f"Student question:\n{question}\n\n"
            f"English answer:\n{english_answer}"
        )

    def _normalization_prompt(self, question: str) -> str:
        return (
            "Convert this student question into one clear, simple English question for "
            "textbook search. The question may be written in English, Nepali Devanagari, "
            "or romanized Nepali typed with English letters. Do not answer the question. "
            "Return only the rewritten English question.\n\n"
            f"Student question:\n{question}"
        )

    def _mock_nepali(
        self,
        question: str,
        english_answer: str,
        sources: list[dict[str, Any]],
    ) -> str:
        topic_text = f"{question} {english_answer} {self._combined_source_text(sources)}".lower()
        known_answer = self._known_nepali_concept_answer(topic_text)

        if known_answer:
            return known_answer

        return (
            "प्राप्त अंग्रेजी उत्तरलाई सरल रूपमा बुझ्दा, यो विषय पाठ्यपुस्तकसँग सम्बन्धित "
            "महत्त्वपूर्ण कुरा हो। मुख्य शब्दहरू ध्यान दिएर पढ्नुहोस्, उदाहरणसँग तुलना "
            "गर्नुहोस्, र आफ्नै शब्दमा छोटो उत्तर लेख्ने अभ्यास गर्नुहोस्।"
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

    def _mock_normalize_question(self, question: str) -> str:
        text = question.lower()

        if (
            "soil erosion" in text
            or "erosion" in text
            or "माटो कटान" in question
            or (
                self._has_any(text, ["mati", "mato", "matto", "maato"])
                and self._has_any(text, ["katan", "katne", "katnu", "bagcha", "bagdai"])
            )
        ):
            return "What is soil erosion?"

        if self._has_any(text, ["oxygen", "aksijan", "akshijan", "अक्सिजन"]):
            return "What is oxygen?"

        if (
            "photosynthesis" in text
            or "प्रकाश संश्लेषण" in question
            or (
                self._has_any(text, ["prakash", "prakaash"])
                and self._has_any(text, ["sansleshan", "samsleshan", "sanshleshan"])
            )
        ):
            return "What is photosynthesis?"

        if self._has_any(text, ["fraction", "bhinn", "vag", "bhaag", "भाग", "भिन्न"]):
            return "What is a fraction?"

        if self._has_any(text, ["mitochondria", "mitochondrion", "mitokondria"]):
            return "What is mitochondria?"

        if self._has_any(text, ["chloroplast", "kloroplast", "chlorophyll"]):
            return "What is chloroplast?"

        if self._has_any(text, ["cell", "koshika", "kosika", "कोषिका"]):
            return "What is a cell?"

        if self._has_any(text, ["energy", "urja", "oorja", "ऊर्जा"]):
            return "What is energy?"

        mixed_topic = self._extract_mixed_language_topic(text)

        if mixed_topic:
            return f"What is {mixed_topic}?"

        return question

    def _extract_mixed_language_topic(self, text: str) -> str:
        markers = [
            " vaneko ",
            " bhaneko ",
            " vanya ",
            " bhanya ",
            " vanne ",
            " bhanne ",
        ]

        if not any(marker in f" {text} " for marker in markers):
            return ""

        topic = f" {text} "
        removable_phrases = [
            " vaneko ",
            " bhaneko ",
            " vanya ",
            " bhanya ",
            " vanne ",
            " bhanne ",
            " ke ho ",
            " k ho ",
            " kya ho ",
            " ho ",
            " ? ",
        ]

        for phrase in removable_phrases:
            topic = topic.replace(phrase, " ")

        topic = " ".join(topic.split()).strip(" ?.,")

        if not topic:
            return ""

        blocked_words = {
            "malai",
            "please",
            "explain",
            "bujhau",
            "bujhaunu",
            "sir",
            "mam",
        }
        words = [word for word in topic.split() if word not in blocked_words]
        topic = " ".join(words)

        if not topic or len(topic) > 80:
            return ""

        return topic

    def _clean_normalized_question(self, text: str) -> str:
        cleaned = text.strip().strip("\"'`")
        cleaned = cleaned.replace("Rewritten English question:", "").strip()
        cleaned = cleaned.splitlines()[0].strip() if cleaned else ""

        if not cleaned:
            return ""

        if len(cleaned) > 180:
            return ""

        if "?" not in cleaned and len(cleaned.split()) > 1:
            cleaned = f"{cleaned}?"

        return cleaned

    def _is_valid_normalized_question(self, text: str) -> bool:
        cleaned = text.strip().strip("?").lower()

        if not cleaned:
            return False

        if cleaned in {"what", "why", "how", "when", "where", "who"}:
            return False

        if len(cleaned.split()) < 3:
            return False

        return True

    def _has_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _is_valid_nepali(self, text: str) -> bool:
        devanagari_count = sum(1 for character in text if "\u0900" <= character <= "\u097f")
        latin_count = sum(1 for character in text if character.isascii() and character.isalpha())

        if devanagari_count < 20:
            return False

        if latin_count > 12:
            return False

        forbidden_markers = ["source", "student question", "english answer", "external"]
        return not any(marker in text.lower() for marker in forbidden_markers)

    def _remove_source_lines(self, text: str) -> str:
        cleaned_lines = []

        for line in text.splitlines():
            lowered = line.lower()

            if "source" in lowered or "बाहरी स्रोत" in line or "स्रोत:" in line:
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()


@lru_cache(maxsize=1)
def get_translation_service() -> TranslationService:
    return TranslationService()
