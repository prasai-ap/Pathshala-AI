"""In-memory student progress store."""

from collections import Counter, defaultdict
from typing import Any


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
}


class StudentStore:
    """Tracks lightweight student progress for the hackathon MVP."""

    def __init__(self) -> None:
        self.students: dict[str, dict[str, Any]] = defaultdict(self._new_progress)

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

    def get_parent_summary(self, student_id: str) -> dict[str, Any]:
        progress = self.students[student_id or DEFAULT_STUDENT_ID]
        strengths = self._strengths(progress)
        weak_topics = sorted(progress["weak_areas"]) or self._lowest_quiz_topics(progress)
        suggested_next_practice = self._suggested_practice(weak_topics, progress)

        return {
            "student_id": student_id or DEFAULT_STUDENT_ID,
            "questions_asked": len(progress["questions_asked"]),
            "topics": sorted(progress["topics"]),
            "quiz_scores": progress["quiz_scores"],
            "weak_areas": sorted(progress["weak_areas"]),
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
        weak_topics = set(progress["weak_areas"])
        strong_quiz_topics = [
            quiz["topic"]
            for quiz in progress["quiz_scores"]
            if quiz.get("percentage", 0) >= 0.75 and quiz["topic"] not in weak_topics
        ]

        if strong_quiz_topics:
            return sorted(set(strong_quiz_topics))

        common_topics = [
            topic
            for topic, _count in progress["topics"].most_common(3)
            if topic not in weak_topics
        ]
        return common_topics or ["asking questions and practicing"]

    def _lowest_quiz_topics(self, progress: dict[str, Any]) -> list[str]:
        if not progress["quiz_scores"]:
            return []

        lowest = sorted(progress["quiz_scores"], key=lambda quiz: quiz["percentage"])
        return [quiz["topic"] for quiz in lowest[:2] if quiz["percentage"] < 0.75]

    def _suggested_practice(
        self,
        weak_topics: list[str],
        progress: dict[str, Any],
    ) -> str:
        if weak_topics:
            return f"Practice {weak_topics[0]} with a few short examples from the textbook."

        if progress["topics"]:
            topic = progress["topics"].most_common(1)[0][0]
            return f"Keep practicing {topic} and try one more short quiz."

        return "Ask one textbook question and try a short quiz after the explanation."

    def _encouraging_note(self, progress: dict[str, Any]) -> str:
        question_count = len(progress["questions_asked"])
        quiz_count = len(progress["quiz_scores"])

        if question_count or quiz_count:
            return "The student is making steady progress. Keep encouraging small daily practice."

        return "A good next step is to ask one simple question from the textbook today."

    def _extract_topics(self, question: str) -> list[str]:
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

        return topic.strip().lower()

    def _split_language_support(self, language_support: str) -> list[str]:
        if not language_support.strip():
            return []

        return [
            part.strip()
            for part in language_support.replace("&", "and").split("and")
            if part.strip()
        ]
