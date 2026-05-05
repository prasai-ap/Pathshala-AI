from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.services.chunker import chunk_text
from backend.services.embedding import get_embedding_service
from backend.services.pdf_loader import PDFExtractionError, extract_pdf_text
from backend.services.vector_store import VectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.app_name = "Pathshala AI"
    app.state.textbook_chunks = []
    app.state.textbook_metadata = None
    app.state.embedding_service = None
    app.state.vector_store = None
    yield


def get_vector_store() -> VectorStore:
    embedding_service = get_embedding_service()

    if app.state.vector_store is None:
        app.state.vector_store = VectorStore(vector_size=embedding_service.dimension)

    return app.state.vector_store


def search_context(question: str, limit: int = 5) -> list[dict[str, object]]:
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    query_embedding = embedding_service.embed_query(question)
    return vector_store.search(query_embedding=query_embedding, limit=limit)


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

        if not chunks:
            raise HTTPException(status_code=400, detail="No readable chunks could be created.")

        embedding_service = get_embedding_service()
        embeddings = embedding_service.embed_texts(chunks)
        vector_store = get_vector_store()
        vector_store.upsert_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadata={
                "filename": filename,
                "page_count": extracted.page_count,
            },
        )
    except PDFExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Vector indexing failed: {exc}") from exc

    app.state.textbook_chunks = chunks
    app.state.textbook_metadata = {
        "filename": filename,
        "page_count": extracted.page_count,
        "chunk_count": len(chunks),
    }

    return {
        "message": "Textbook uploaded, chunked, and indexed in Qdrant.",
        "filename": filename,
        "page_count": extracted.page_count,
        "chunk_count": len(chunks),
    }


@app.get("/debug/search-context")
async def debug_search_context(question: str, limit: int = 5) -> dict[str, object]:
    try:
        context = search_context(question=question, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Vector search failed: {exc}") from exc

    return {"question": question, "matches": context}
