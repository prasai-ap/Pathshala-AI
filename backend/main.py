"""
Pathshala AI - FastAPI Backend
Bilingual AI tutor for rural primary education in Nepal
"""
import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from services.pdf_loader import PDFLoader, PDFLoadError
from services.chunker import Chunker
from services.embedding import EmbeddingService
from services.qdrant_store import QdrantStore
from models.schemas import TextbookUploadResponse
from services.llm_client import get_default_client
from agents.retriever_agent import RetrieverAgent
from agents.tutor_agent import TutorAgent
from agents.quiz_agent import QuizAgent
from services.student_store import StudentStore

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Pathshala AI",
    description="Bilingual AI tutor for rural primary education in Nepal",
    version="0.1.0"
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for chunks (temporary)
textbook_chunks_store = {}  # {upload_id: {filename, chunks: [...], total_chars}}

# Initialize services
pdf_loader = PDFLoader()
chunker = Chunker(chunk_size=512, chunk_overlap=64)

# Embedding and vector store (Qdrant)
embedding_service = EmbeddingService()
qdrant_store = QdrantStore(collection_name=os.getenv("QDRANT_COLLECTION", "textbooks"))

# LLM client and agents
llm_client = get_default_client()
retriever_agent = RetrieverAgent(embedding_service, qdrant_store)
tutor_agent = TutorAgent(llm_client, retriever_agent)
quiz_agent = QuizAgent(llm_client, retriever_agent)
student_store = StudentStore()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pathshala-ai-backend",
        "version": "0.1.0"
    }


@app.post("/upload-textbook", response_model=TextbookUploadResponse)
async def upload_textbook(file: UploadFile = File(...)):
    """
    Upload and process a textbook PDF
    
    Args:
        file: PDF file to upload
    
    Returns:
        Upload response with chunks information
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )
        
        # Extract text from PDF
        extracted_text = await pdf_loader.load_pdf_from_bytes(file_bytes, file.filename)
        
        # Split into chunks
        chunks = chunker.chunk_text(extracted_text)
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No readable content found in PDF"
            )
        
        # Generate upload ID and store chunks (in-memory)
        upload_id = str(uuid.uuid4())
        textbook_chunks_store[upload_id] = {
            "filename": file.filename,
            "chunks": chunks,
            "total_chars": len(extracted_text)
        }

        # Embed chunks and store into Qdrant (best-effort)
        try:
            embeddings = embedding_service.embed_texts(chunks)
            qdrant_store.upsert_chunks(upload_id=upload_id, filename=file.filename, chunks=chunks, embeddings=embeddings)
            stored_in_qdrant = True
        except Exception as e:
            # Don't fail the upload if Qdrant/embeddings fail; log and continue
            stored_in_qdrant = False
            print(f"Warning: failed to store embeddings in Qdrant: {e}")

        message = f"Successfully processed {file.filename} into {len(chunks)} chunks"
        if stored_in_qdrant:
            message += " and stored embeddings in Qdrant"

        return TextbookUploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            status="success",
            num_chunks=len(chunks),
            total_characters=len(extracted_text),
            message=message
        )
    
    except PDFLoadError as e:
        raise HTTPException(
            status_code=400,
            detail=f"PDF processing error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/textbooks/{upload_id}/preview")
async def get_textbook_preview(upload_id: str, chunk_count: int = 5):
    """
    Get a preview of uploaded textbook chunks
    
    Args:
        upload_id: Upload ID
        chunk_count: Number of chunks to preview
    
    Returns:
        Preview of chunks
    """
    if upload_id not in textbook_chunks_store:
        raise HTTPException(
            status_code=404,
            detail="Textbook not found"
        )
    
    textbook_data = textbook_chunks_store[upload_id]
    chunks = textbook_data["chunks"][:chunk_count]
    
    return {
        "upload_id": upload_id,
        "filename": textbook_data["filename"],
        "total_chunks": len(textbook_data["chunks"]),
        "preview_chunks": chunk_count,
        "chunks": chunks
    }


@app.post("/search-context")
async def search_context(question: str, top_k: int = 5):
    """
    Search Qdrant for top relevant chunks for a question

    Args:
        question: The user's question
        top_k: Number of top chunks to return

    Returns:
        List of matching chunks with scores and payload
    """
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    try:
        qvec = embedding_service.embed_text(question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

    try:
        results = qdrant_store.search(query_vector=qvec, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {e}")

    # Return payloads and scores
    out = []
    for r in results:
        payload = r.get("payload", {})
        out.append({
            "id": r.get("id"),
            "score": r.get("score"),
            "content": payload.get("content"),
            "upload_id": payload.get("upload_id"),
            "filename": payload.get("filename"),
            "sequence": payload.get("sequence"),
        })

    return {"question": question, "results": out}


@app.post("/ask")
async def ask_question(question: str, student_id: str = "anonymous", top_k: int = 5):
    """
    Ask a tutoring question. Returns English and Nepali simple explanations,
    3 quiz questions, and the retrieved sources used.
    """
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    # Retrieve textbook context
    contexts = await retriever_agent.retrieve_context(question, top_k=top_k)

    # Tutor agent answer (English and Nepali)
    tutor_resp = await tutor_agent.answer_question(question=question, student_id=student_id, language="English")

    # Quiz generation (3 questions)
    quiz_resp = await quiz_agent.generate_quiz(topic=question, num_questions=3, language="English")

    # Build response
    response = {
        "answer_english": tutor_resp.get("answer_english", ""),
        "answer_nepali": tutor_resp.get("answer_nepali", ""),
        "quiz_questions": quiz_resp.get("quiz_questions", []),
        "retrieved_sources": [{"id": c.get("id"), "score": c.get("score"), "content": c.get("content"), "filename": c.get("filename"), "upload_id": c.get("upload_id")} for c in contexts]
    }

    # If no retrieved content, indicate insufficient context
    if not contexts:
        response["note"] = "Insufficient textbook context found for this question. Please upload relevant textbook."

    return response


@app.post("/submit-quiz")
async def submit_quiz(payload: dict):
    """
    Submit quiz results for a student. Expects JSON with:
    - student_id (string)
    - student_name (optional)
    - topic (string)
    - score (int)
    - total (int)
    - language (optional)
    """
    student_id = payload.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")

    # Ensure student exists
    await student_store.create_student(student_id, name=payload.get("student_name", ""), language=payload.get("language", ""))

    # Update progress
    progress = {
        "quiz": {"topic": payload.get("topic"), "score": payload.get("score"), "total": payload.get("total")},
        "language": payload.get("language")
    }
    s = await student_store.update_progress(student_id, progress)

    return {"status": "ok", "student": s.get("student_id"), "quiz_count": len(s.get("quiz_scores", []))}


@app.get("/parent-summary/{student_id}")
async def parent_summary(student_id: str):
    """
    Return a simple parent-friendly summary for a student
    """
    summary = await student_store.compute_summary(student_id)
    if summary.get("message"):
        raise HTTPException(status_code=404, detail=summary.get("message"))

    # Build readable summary
    strengths = summary.get("strengths", [])
    weak_topics = summary.get("weak_topics", [])
    suggested = summary.get("suggested_next_practice", [])
    note = summary.get("encouraging_note", "Keep practicing!")

    return {
        "student_id": student_id,
        "name": summary.get("name"),
        "strengths": strengths,
        "weak_topics": weak_topics,
        "suggested_next_practice": suggested,
        "encouraging_note": note,
        "summary": summary.get("summary", {})
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV", "development") == "development"
    )
