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
