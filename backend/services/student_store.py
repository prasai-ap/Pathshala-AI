"""In-memory student progress store."""

from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Any
from uuid import uuid4


DEFAULT_STUDENT_ID = "demo-student"

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "explain",
    "for",
    "how",
    "in",
    "is",
    "me",
    "of",
    "the",
    "to",
    "what",
    "why",
    "vaneko",
    "bhaneko",
    "vanya",
    "bhanya",
    "vane",
    "bhanne",
    "ke",
    "ho",
    "vana",
}

TOPIC_ALIASES = {
    "photosynthesis": "प्रकाश संश्लेषण",
    "prakash sansleshan": "प्रकाश संश्लेषण",
    "soil erosion": "माटो कटान",
    "mato katan": "माटो कटान",
    "fraction": "भिन्न",
    "oxygen": "अक्सिजन",
    "cell": "कोषिका",
    "energy": "ऊर्जा",
}


class StudentStore:
    """Tracks lightweight student progress for the hackathon MVP."""

    def __init__(self) -> None:
        self.students: dict[str, dict[str, Any]] = defaultdict(self._new_progress)
        self.quizzes: dict[str, dict[str, Any]] = {}

    def record_question(
        self,
        student_id: str,
        question: str,
        topics: list[str] | None = None,
        language_support: str = "English and Nepali",
    ) -> dict[str, Any]:
        progress = self.students[student_id or DEFAULT_STUDENT_ID]
        normalized_topics = self._normalize_topics(topics) or self._extract_topics(question)

        progress["questions_asked"].append(question)
        progress["topics"].update(normalized_topics)
        progress["language_support_used"].update(self._split_language_support(language_support))
        return progress

    def submit_quiz(
        self,
        student_id: str,
        topic: str,
        score: int,
        total: int,
        weak_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        if total <= 0:
            raise ValueError("total must be greater than zero.")

        if score < 0 or score > total:
            raise ValueError("score must be between zero and total.")

        progress = self.students[student_id or DEFAULT_STUDENT_ID]
        normalized_topic = self._normalize_topic(topic) or "general practice"
        percentage = score / total

        progress["topics"].update([normalized_topic])
        progress["quiz_scores"].append(
            {
                "topic": normalized_topic,
                "score": score,
                "total": total,
                "percentage": round(percentage, 2),
            }
        )

        if percentage < 0.6:
            progress["weak_areas"].update([normalized_topic])

        progress["weak_areas"].update(self._normalize_topics(weak_areas))
        return progress

    def create_quiz(
        self,
        student_id: str,
        topic: str,
        items: list[dict[str, str]],
    ) -> str:
        quiz_id = str(uuid4())
        normalized_topic = self._normalize_topic(topic) or "general practice"
        normalized_items = [
            {
                "question": item.get("question", "").strip(),
                "expected_answer": item.get("expected_answer", "").strip(),
                "weak_area": self._normalize_topic(item.get("weak_area")) or normalized_topic,
            }
            for item in items
            if item.get("question", "").strip()
        ]

        self.quizzes[quiz_id] = {
            "student_id": student_id or DEFAULT_STUDENT_ID,
            "topic": normalized_topic,
            "items": normalized_items[:3],
        }
        return quiz_id

    def grade_quiz(
        self,
        student_id: str,
        quiz_id: str,
        answers: list[str],
    ) -> dict[str, Any]:
        if quiz_id not in self.quizzes:
            raise ValueError("quiz_id was not found. Ask a question to create a quiz first.")

        quiz = self.quizzes[quiz_id]
        stored_student_id = quiz["student_id"]
        request_student_id = student_id or DEFAULT_STUDENT_ID

        if stored_student_id != request_student_id:
            raise ValueError("quiz_id does not belong to this student.")

        results = []
        weak_areas = []

        for index, item in enumerate(quiz["items"]):
            student_answer = answers[index].strip() if index < len(answers) else ""
            expected_answer = item["expected_answer"]
            is_correct = self._is_answer_correct(student_answer, expected_answer)

            if not is_correct:
                weak_areas.append(item["weak_area"])

            results.append(
                {
                    "question": item["question"],
                    "student_answer": student_answer,
                    "is_correct": is_correct,
                    "expected_answer": expected_answer,
                    "weak_area": item["weak_area"],
                }
            )

        score = sum(1 for result in results if result["is_correct"])
        total = len(results)
        progress = self.submit_quiz(
            student_id=request_student_id,
            topic=quiz["topic"],
            score=score,
            total=total,
            weak_areas=weak_areas,
        )

        return {
            "student_id": request_student_id,
            "quiz_id": quiz_id,
            "score": score,
            "total": total,
            "weak_areas": sorted(progress["weak_areas"]),
            "results": results,
        }

    def get_parent_summary(self, student_id: str) -> dict[str, Any]:
        progress = self.students[student_id or DEFAULT_STUDENT_ID]
        strengths = self._strengths(progress)
        weak_topics = self._weak_topics(progress)
        suggested_next_practice = self._suggested_practice(weak_topics, progress)
        topics = self._clean_topic_list(progress["topics"])
        weak_areas = self._clean_topic_list(progress["weak_areas"])

        return {
            "student_id": student_id or DEFAULT_STUDENT_ID,
            "questions_asked": len(progress["questions_asked"]),
            "topics": topics,
            "quiz_scores": progress["quiz_scores"],
            "weak_areas": weak_areas,
            "language_support_used": sorted(progress["language_support_used"]),
            "strengths": strengths,
            "weak_topics": weak_topics,
            "suggested_next_practice": suggested_next_practice,
            "encouraging_note": self._encouraging_note(progress),
        }

    def _new_progress(self) -> dict[str, Any]:
        return {
            "questions_asked": [],
            "topics": Counter(),
            "quiz_scores": [],
            "weak_areas": Counter(),
            "language_support_used": Counter(),
        }

    def _strengths(self, progress: dict[str, Any]) -> list[str]:
        weak_topics = set(self._weak_topics(progress))
        strong_quiz_topics = [
            self._display_topic(quiz["topic"])
            for quiz in progress["quiz_scores"]
            if quiz.get("percentage", 0) >= 0.75
            and self._display_topic(quiz["topic"]) not in weak_topics
        ]

        if strong_quiz_topics:
            return sorted(set(topic for topic in strong_quiz_topics if topic))

        common_topics = [
            self._display_topic(topic)
            for topic, _count in progress["topics"].most_common(3)
            if self._display_topic(topic) not in weak_topics
        ]
        common_topics = [topic for topic in common_topics if topic]
        return common_topics or ["प्रश्न सोध्ने र अभ्यास गर्ने बानी"]

    def _weak_topics(self, progress: dict[str, Any]) -> list[str]:
        weak_topics = self._clean_topic_list(progress["weak_areas"])
        if weak_topics:
            return weak_topics

        return self._lowest_quiz_topics(progress)

    def _lowest_quiz_topics(self, progress: dict[str, Any]) -> list[str]:
        if not progress["quiz_scores"]:
            return []

        lowest = sorted(progress["quiz_scores"], key=lambda quiz: quiz["percentage"])
        return [
            self._display_topic(quiz["topic"])
            for quiz in lowest[:2]
            if quiz["percentage"] < 0.75 and self._display_topic(quiz["topic"])
        ]

    def _suggested_practice(
        self,
        weak_topics: list[str],
        progress: dict[str, Any],
    ) -> str:
        if weak_topics:
            return (
                f"{weak_topics[0]} का मुख्य शब्द, परिभाषा, र एउटा उदाहरण फेरि "
                "पाठ्यपुस्तकबाट पढेर ३ छोटा प्रश्न अभ्यास गर्नुहोस्।"
            )

        if progress["topics"]:
            topic = self._display_topic(progress["topics"].most_common(1)[0][0])
            return f"{topic} मा अभ्यास जारी राख्नुहोस् र अर्को छोटो क्विज प्रयास गर्नुहोस्।"

        return "आज पाठ्यपुस्तकबाट एउटा सरल प्रश्न सोधेर उत्तरपछि छोटो क्विज प्रयास गर्नुहोस्।"

    def _encouraging_note(self, progress: dict[str, Any]) -> str:
        question_count = len(progress["questions_asked"])
        quiz_count = len(progress["quiz_scores"])

        if question_count or quiz_count:
            latest_score = progress["quiz_scores"][-1] if progress["quiz_scores"] else None
            if latest_score and latest_score.get("percentage", 0) >= 0.75:
                return "विद्यार्थीले राम्रो प्रगति देखाएको छ। छोटो दैनिक अभ्यास जारी राख्नुहोस्।"
            if latest_score:
                return "विद्यार्थीले प्रयास गरिरहेको छ। गलत भएका प्रश्नलाई उदाहरणसहित फेरि अभ्यास गराउँदा सुधार हुन्छ।"
            return "विद्यार्थीले प्रश्न सोध्ने राम्रो सुरुवात गरेको छ। अब छोटो अभ्यास थप्नु उपयोगी हुन्छ।"

        return "आज पाठ्यपुस्तकबाट एउटा सरल प्रश्न सोध्नु राम्रो सुरुवात हुनेछ।"

    def _extract_topics(self, question: str) -> list[str]:
        mapped_topic = self._known_topic(question)
        if mapped_topic:
            return [mapped_topic]

        words = [
            word.strip(".,?!:;()[]{}\"'").lower()
            for word in question.split()
        ]
        topics = [
            word
            for word in words
            if len(word) > 2 and word not in STOPWORDS
        ]
        return topics[:3] or ["general question"]

    def _normalize_topics(self, topics: list[str] | None) -> list[str]:
        if not topics:
            return []

        return [
            normalized
            for topic in topics
            if (normalized := self._normalize_topic(topic))
        ]

    def _normalize_topic(self, topic: str | None) -> str:
        if not topic:
            return ""

        cleaned = " ".join(topic.strip().lower().split())
        known_topic = self._known_topic(cleaned)

        if known_topic:
            return known_topic

        if self._is_noisy_topic(cleaned):
            return ""

        return cleaned

    def _split_language_support(self, language_support: str) -> list[str]:
        if not language_support.strip():
            return []

        return [
            part.strip()
            for part in language_support.replace("&", "and").split("and")
            if part.strip()
        ]

    def _is_answer_correct(self, student_answer: str, expected_answer: str) -> bool:
        normalized_student = self._normalize_answer(student_answer)
        normalized_expected = self._normalize_answer(expected_answer)

        if not normalized_student or not normalized_expected:
            return False

        if normalized_student in normalized_expected or normalized_expected in normalized_student:
            return True

        student_tokens = set(normalized_student.split())
        expected_tokens = set(normalized_expected.split())
        overlap = len(student_tokens & expected_tokens) / max(len(expected_tokens), 1)
        similarity = SequenceMatcher(None, normalized_student, normalized_expected).ratio()

        return overlap >= 0.45 or similarity >= 0.7

    def _normalize_answer(self, answer: str) -> str:
        return " ".join(
            word.strip(".,?!:;()[]{}\"'").lower()
            for word in answer.split()
            if word.strip(".,?!:;()[]{}\"'")
        )

    def _known_topic(self, text: str) -> str:
        normalized = " ".join(text.lower().replace("?", " ").split())

        if "photosynthesis" in normalized or (
            "prakash" in normalized and "sansleshan" in normalized
        ) or "प्रकाश संश्लेषण" in text:
            return "प्रकाश संश्लेषण"

        if "soil erosion" in normalized or (
            "mato" in normalized and "katan" in normalized
        ) or "माटो कटान" in text:
            return "माटो कटान"

        for key, value in TOPIC_ALIASES.items():
            if key in normalized or value in text:
                return value

        return ""

    def _display_topic(self, topic: str) -> str:
        normalized = self._normalize_topic(topic)
        return normalized if normalized and not self._is_noisy_topic(normalized) else ""

    def _clean_topic_list(self, counter: Counter) -> list[str]:
        topics = []

        for topic, _count in counter.most_common():
            display_topic = self._display_topic(topic)
            if display_topic and display_topic not in topics:
                topics.append(display_topic)

        return topics[:5]

    def _is_noisy_topic(self, topic: str) -> bool:
        if not topic:
            return True

        if topic in STOPWORDS:
            return True

        if len(topic) < 3:
            return True

        devanagari_count = sum(1 for character in topic if "\u0900" <= character <= "\u097f")
        ascii_count = sum(1 for character in topic if character.isascii() and character.isalpha())
        symbol_count = sum(1 for character in topic if character in "/\\|;:{}[]'\"`~")
        suspicious_markers = ["kf7", "tsnf", "cfwf", ";sf", "ofsf"]

        if any(marker in topic for marker in suspicious_markers):
            return True

        if symbol_count >= 2:
            return True

        if ascii_count and devanagari_count == 0 and len(topic) > 30:
            return True

        return False
