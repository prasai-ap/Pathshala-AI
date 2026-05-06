from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class TextbookUploadResponse(BaseModel):
    message: str
    filename: str
    page_count: int
    chunk_count: int
    extraction_method: str | None = None


class SearchMatch(BaseModel):
    score: float
    text: str
    metadata: dict[str, object]


class SearchContextResponse(BaseModel):
    question: str
    matches: list[SearchMatch]


class AskRequest(BaseModel):
    question: str
    student_id: str = "demo-student"
    language_support: str = "English and Nepali"


class RetrievedSource(BaseModel):
    score: float
    text: str
    metadata: dict[str, object]


class AskResponse(BaseModel):
    normalized_question: str | None = None
    answer_english: str
    answer_nepali: str
    quiz_id: str | None = None
    quiz_questions: list[str]
    retrieved_sources: list[RetrievedSource]


class SubmitQuizRequest(BaseModel):
    student_id: str = "demo-student"
    topic: str
    score: int
    total: int
    weak_areas: list[str] = Field(default_factory=list)


class SubmitQuizResponse(BaseModel):
    student_id: str
    topic: str
    score: int
    total: int
    weak_areas: list[str]


class AutoGradeQuizRequest(BaseModel):
    student_id: str = "demo-student"
    quiz_id: str
    answers: list[str] = Field(default_factory=list)


class GradedQuizItem(BaseModel):
    question: str
    student_answer: str
    is_correct: bool
    expected_answer: str
    weak_area: str


class AutoGradeQuizResponse(BaseModel):
    student_id: str
    quiz_id: str
    score: int
    total: int
    weak_areas: list[str]
    results: list[GradedQuizItem]


class ParentSummaryResponse(BaseModel):
    student_id: str
    questions_asked: int
    topics: list[str]
    quiz_scores: list[dict[str, object]]
    weak_areas: list[str]
    language_support_used: list[str]
    strengths: list[str]
    weak_topics: list[str]
    suggested_next_practice: str
    encouraging_note: str
