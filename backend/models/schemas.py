from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class TextbookUploadResponse(BaseModel):
    message: str
    filename: str
    page_count: int
    chunk_count: int


class SearchMatch(BaseModel):
    score: float
    text: str
    metadata: dict[str, object]


class SearchContextResponse(BaseModel):
    question: str
    matches: list[SearchMatch]


class AskRequest(BaseModel):
    question: str


class RetrievedSource(BaseModel):
    score: float
    text: str
    metadata: dict[str, object]


class AskResponse(BaseModel):
    answer_english: str
    answer_nepali: str
    quiz_questions: list[str]
    retrieved_sources: list[RetrievedSource]
