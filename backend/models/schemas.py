from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class TextbookUploadResponse(BaseModel):
    message: str
    filename: str
    page_count: int
    chunk_count: int
