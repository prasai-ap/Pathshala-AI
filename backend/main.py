from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.services.chunker import chunk_text
from backend.services.pdf_loader import PDFExtractionError, extract_pdf_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.app_name = "Pathshala AI"
    app.state.textbook_chunks = []
    app.state.textbook_metadata = None
    yield


app = FastAPI(
    title="Pathshala AI API",
    description="Backend API skeleton for a bilingual AI tutor for rural primary education in Nepal.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "pathshala-ai-backend"}


@app.post("/upload-textbook")
async def upload_textbook(file: UploadFile = File(...)) -> dict[str, object]:
    filename = file.filename or "uploaded-textbook.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()

    try:
        extracted = extract_pdf_text(pdf_bytes)
        chunks = chunk_text(extracted.text)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not chunks:
        raise HTTPException(status_code=400, detail="No readable chunks could be created.")

    app.state.textbook_chunks = chunks
    app.state.textbook_metadata = {
        "filename": filename,
        "page_count": extracted.page_count,
        "chunk_count": len(chunks),
    }

    return {
        "message": "Textbook uploaded and chunked in memory.",
        "filename": filename,
        "page_count": extracted.page_count,
        "chunk_count": len(chunks),
    }
