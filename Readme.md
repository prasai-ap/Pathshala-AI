# Pathshala AI

Pathshala AI is a bilingual AI tutor for rural primary education in Nepal.

## Problem

Many rural primary students in Nepal have limited access to personalized learning support, bilingual explanations, and parent-friendly progress feedback.

## Solution

Pathshala AI will help students ask questions in Nepali or English, retrieve grounded context from uploaded curriculum material, receive simple tutoring explanations, practice with quizzes, and generate summaries for parents.

## Architecture

- FastAPI backend for API endpoints and agent orchestration
- Streamlit frontend for the hackathon MVP interface
- Qdrant vector database for curriculum retrieval
- Agent placeholders for supervision, retrieval, tutoring, quizzes, and parent summaries

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

Backend health check:

```bash
curl http://localhost:8000/health
```

Frontend:

```bash
http://localhost:8501
```
