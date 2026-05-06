import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.agents.quiz_agent import QuizAgent
from backend.agents.retriever_agent import RetrieverAgent
from backend.agents.tutor_agent import TutorAgent
from backend.models.schemas import (
    AskRequest,
    AskResponse,
    AutoGradeQuizRequest,
    AutoGradeQuizResponse,
    ParentSummaryResponse,
    SubmitQuizRequest,
    SubmitQuizResponse,
)
from backend.services.chunker import chunk_text
from backend.services.config import get_config, log_startup_config
from backend.services.embedding import get_embedding_service
from backend.services.llm_client import LLMClientError, get_llm_client
from backend.services.pdf_loader import PDFExtractionError, extract_pdf_text
from backend.services.student_store import DEFAULT_STUDENT_ID, StudentStore
from backend.services.translation_service import get_translation_service
from backend.services.vector_store import VectorStore


logging.basicConfig(level=logging.INFO)
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_startup_config(config)
    app.state.app_name = config.app_name
    app.state.textbook_chunks = []
    app.state.textbook_metadata = None
    app.state.embedding_service = None
    app.state.student_store = StudentStore()
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
    matches = vector_store.search(query_embedding=query_embedding, limit=limit * 2)
    return dedupe_sources(matches)[:limit]


def dedupe_sources(sources: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped = []
    seen = set()

    for source in sources:
        metadata = source.get("metadata", {})
        key = (
            metadata.get("filename") if isinstance(metadata, dict) else None,
            metadata.get("chunk_index") if isinstance(metadata, dict) else None,
            source.get("text", ""),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(source)

    return deduped


def get_student_store() -> StudentStore:
    return app.state.student_store


app = FastAPI(
    title=f"{config.app_name} API",
    description="Backend API skeleton for a bilingual AI tutor for rural primary education in Nepal.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "pathshala-ai-backend"}


@app.post("/upload-textbook")
def upload_textbook(file: UploadFile = File(...)) -> dict[str, object]:
    filename = file.filename or "uploaded-textbook.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = file.file.read()

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
        "extraction_method": extracted.extraction_method,
    }

    return {
        "message": "Textbook uploaded, chunked, and indexed in Qdrant.",
        "filename": filename,
        "page_count": extracted.page_count,
        "chunk_count": len(chunks),
        "extraction_method": extracted.extraction_method,
    }


@app.get("/debug/search-context")
def debug_search_context(question: str, limit: int = 5) -> dict[str, object]:
    try:
        context = search_context(question=question, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Vector search failed: {exc}") from exc

    return {"question": question, "matches": context}


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    try:
        translation_service = get_translation_service()
        normalized_question = translation_service.normalize_question(request.question)
        retriever_agent = RetrieverAgent(search_context=search_context)
        sources = retriever_agent.retrieve(normalized_question, limit=5)
        student_store = get_student_store()
        student_store.record_question(
            student_id=request.student_id,
            question=request.question,
            language_support=request.language_support,
        )

        llm_client = get_llm_client()
        tutor_agent = TutorAgent(llm_client=llm_client)
        quiz_agent = QuizAgent(llm_client=llm_client)

        answer_english = tutor_agent.answer_english(normalized_question, sources)
        answer_nepali = translation_service.to_nepali(
            question=request.question,
            english_answer=answer_english,
            sources=sources,
        )
        quiz_items = quiz_agent.generate_items(normalized_question, sources)
        quiz_questions = [item["question"] for item in quiz_items]
        quiz_id = student_store.create_quiz(
            student_id=request.student_id,
            topic=normalized_question,
            items=quiz_items,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Tutoring workflow failed: {exc}") from exc

    return AskResponse(
        normalized_question=normalized_question,
        answer_english=answer_english,
        answer_nepali=answer_nepali,
        quiz_id=quiz_id,
        quiz_questions=quiz_questions,
        retrieved_sources=sources,
    )


@app.post("/grade-quiz", response_model=AutoGradeQuizResponse)
def grade_quiz(request: AutoGradeQuizRequest) -> AutoGradeQuizResponse:
    try:
        result = get_student_store().grade_quiz(
            student_id=request.student_id,
            quiz_id=request.quiz_id,
            answers=request.answers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AutoGradeQuizResponse(**result)


@app.post("/submit-quiz", response_model=SubmitQuizResponse)
def submit_quiz_result(request: SubmitQuizRequest) -> SubmitQuizResponse:
    try:
        student_id = request.student_id or DEFAULT_STUDENT_ID
        progress = get_student_store().submit_quiz(
            student_id=student_id,
            topic=request.topic,
            score=request.score,
            total=request.total,
            weak_areas=request.weak_areas,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SubmitQuizResponse(
        student_id=student_id,
        topic=request.topic,
        score=request.score,
        total=request.total,
        weak_areas=sorted(progress["weak_areas"]),
    )


@app.get("/parent-summary/{student_id}", response_model=ParentSummaryResponse)
def parent_summary(student_id: str) -> ParentSummaryResponse:
    summary = get_student_store().get_parent_summary(student_id)
    return ParentSummaryResponse(**summary)
