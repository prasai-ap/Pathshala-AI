"""
Student Store Service - In-memory implementation

This provides a minimal in-memory student progress store for development
and testing. It tracks questions asked, topics, quiz scores, weak areas,
and language usage. Data is not persisted across process restarts.
"""

from collections import defaultdict
from statistics import mean
from typing import Dict, Any, List
import time


class StudentStore:
    """In-memory student store."""

    def __init__(self):
        # store structure: student_id -> data dict
        self.store: Dict[str, Dict[str, Any]] = {}

    async def create_student(self, student_id: str, name: str = "", grade: int = 0, language: str = ""):
        if student_id in self.store:
            return self.store[student_id]
        self.store[student_id] = {
            "student_id": student_id,
            "name": name,
            "grade": grade,
            "preferred_language": language,
            "questions_asked": [],  # list of {question, topic, timestamp}
            "topics": defaultdict(list),  # topic -> list of quiz scores
            "quiz_scores": [],  # list of {topic, score, total, timestamp}
            "language_usage": defaultdict(int),
            "created_at": time.time(),
        }
        return self.store[student_id]

    async def get_student(self, student_id: str):
        return self.store.get(student_id)

    async def update_progress(self, student_id: str, progress_data: Dict[str, Any]):
        """
        Update student progress with a progress_data dict. Supported keys:
        - question (str), topic (str)
        - quiz: {topic, score, total}
        - language (str)
        """
        if student_id not in self.store:
            await self.create_student(student_id)

        s = self.store[student_id]

        # Track question asked
        question = progress_data.get("question")
        topic = progress_data.get("topic")
        if question:
            s["questions_asked"].append({"question": question, "topic": topic, "timestamp": time.time()})
            if topic:
                s["topics"][topic]  # ensure key exists

        # Track quiz submission
        quiz = progress_data.get("quiz")
        if quiz:
            t = quiz.get("topic") or topic or "general"
            score = quiz.get("score")
            total = quiz.get("total") or 0
            entry = {"topic": t, "score": score, "total": total, "timestamp": time.time()}
            s["quiz_scores"].append(entry)
            if isinstance(score, (int, float)) and total:
                pct = (score / total) * 100 if total else 0
                s["topics"][t].append(pct)

        # Track language
        language = progress_data.get("language")
        if language:
            s["language_usage"][language] += 1

        return s

    async def compute_summary(self, student_id: str) -> Dict[str, Any]:
        s = self.store.get(student_id)
        if not s:
            return {"message": "No data for student"}

        # Compute average per topic
        topic_avgs: Dict[str, float] = {}
        for topic, scores in s["topics"].items():
            if scores:
                topic_avgs[topic] = mean(scores)

        # Determine strengths and weak topics
        strengths = sorted([t for t, a in topic_avgs.items() if a >= 80], key=lambda x: -topic_avgs[x])
        weak = sorted([t for t, a in topic_avgs.items() if a < 70], key=lambda x: topic_avgs[x])

        # Suggested next practice: prioritize weak topics
        suggested = weak[:3] if weak else (sorted(topic_avgs.keys(), key=lambda x: -topic_avgs[x])[:3])

        # Encouraging note
        note = "Keep practicing regularly — small steps every day help!"

        return {
            "student_id": student_id,
            "name": s.get("name"),
            "strengths": strengths,
            "weak_topics": weak,
            "suggested_next_practice": suggested,
            "last_updated": time.time(),
            "summary": {
                "topic_averages": topic_avgs,
                "total_quizzes": len(s.get("quiz_scores", [])),
            },
            "encouraging_note": note,
        }

