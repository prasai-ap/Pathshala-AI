# Pathshala AI

Pathshala AI is a bilingual AI tutor for rural primary education in Nepal.

## Problem

Many rural primary students in Nepal have limited access to personalized learning support, bilingual explanations, and parent-friendly progress feedback.

## Solution

Pathshala AI will help students ask questions in Nepali or English, retrieve grounded context from uploaded curriculum material, receive simple tutoring explanations, practice with quizzes, and generate summaries for parents.

## Architecture

- FastAPI backend for API endpoints and agent orchestration
- Streamlit frontend for the hackathon MVP interface
- Sentence-transformers embedding service for multilingual chunk and query vectors
- Qdrant vector database for curriculum chunk storage and similarity search
- Agent placeholders for supervision, retrieval, tutoring, quizzes, and parent summaries

## Upload Flow

1. Open the Streamlit frontend at `http://localhost:8501`.
2. Upload a textbook or worksheet PDF in the Upload section.
3. The frontend posts the PDF to `POST /upload-textbook`.
4. The backend extracts text with PyMuPDF, chunks the text, embeds each chunk with sentence-transformers, and stores vectors in Qdrant.
5. The UI shows the uploaded filename, page count, and chunk count.

Invalid PDFs, empty files, and PDFs without readable text return a `400` error with a short message.

## RAG Flow

1. Upload a PDF textbook through Streamlit or `POST /upload-textbook`.
2. The backend chunks the extracted text and indexes each chunk in Qdrant with filename and chunk metadata.
3. A student question is embedded with the same sentence-transformer model.
4. `search_context(question)` retrieves the most relevant chunks from Qdrant.
5. `POST /ask` sends the question and retrieved textbook chunks through the tutoring workflow.
6. The retriever agent returns relevant sources, the tutor agent creates simple English and Nepali explanations, and the quiz agent creates three practice questions.
7. `GET /debug/search-context?question=...` returns raw matching chunks for testing.

The tutoring prompts instruct the model to use textbook context only, explain like a primary-school tutor, keep answers simple, and say when the retrieved context is insufficient.

Example ask request:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What is photosynthesis?\"}"
```

The response includes `answer_english`, `answer_nepali`, `quiz_questions`, and `retrieved_sources`.

## AMD MI300X Usage Plan

The MVP will target an AMD MI300X-hosted open model for high-throughput bilingual tutoring, quiz generation, and report summarization. The backend LLM client will isolate model calls so the app can switch between local development and MI300X inference during deployment.

## MVP Roadmap

1. Add PDF upload and curriculum text extraction
2. Chunk textbook content and index embeddings in Qdrant
3. Build retrieval-grounded tutoring responses
4. Add bilingual quiz generation
5. Track simple student progress
6. Generate parent summaries in clear Nepali and English

## Local Development

```bash
docker compose up
```

The frontend uses `requirements-frontend.txt` so it does not install the backend ML stack. The backend uses CPU PyTorch wheels for sentence-transformers during local Docker development.

Backend health check:

```bash
curl http://localhost:8000/health
```

Frontend:

```bash
http://localhost:8501
```
