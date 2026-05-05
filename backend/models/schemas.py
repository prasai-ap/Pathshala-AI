"""
Data models and schemas for Pathshala AI
"""
from pydantic import BaseModel
from typing import Optional, List


class StudentInfo(BaseModel):
    """Student information schema"""
    student_id: str
    name: str
    grade: int
    language: str  # "Nepali" or "English"


class Question(BaseModel):
    """Question schema"""
    text: str
    language: str
    student_id: str


class Answer(BaseModel):
    """Answer schema"""
    question_id: str
    answer_text: str
    student_id: str


class Quiz(BaseModel):
    """Quiz schema"""
    student_id: str
    topic: str
    num_questions: int


class QuizResult(BaseModel):
    """Quiz result schema"""
    quiz_id: str
    student_id: str
    score: float
    total_questions: int


class ParentReport(BaseModel):
    """Parent report schema"""
    student_id: str
    period: str  # "weekly", "monthly"
    language: str
