# Pathshala AI — Agentic AI Tutor for Rural Primary Students (Nepal)

## Problem Statement
Rural primary school students in Nepal often struggle to understand textbook content due to language barriers and lack of access to tutors. Teachers and parents need quick visibility into student understanding and weak areas.

## Solution
Pathshala AI is an agentic AI tutor that:
- Accepts a textbook PDF upload
- Answers student questions grounded in the textbook
- Supports bilingual explanations in **simple English** and **simple Nepali**
- Generates a short quiz
- Produces a parent/teacher summary of weak topics and progress

## Architecture (Text Diagram)
```
[Streamlit UI]
      |
      v
[FastAPI Backend] ---> [PDF Loader] ---> [Chunker]
      |                       |              |
      |                       v              v
      |                 [Vector Store (Qdrant)]
      |                       |
      v                       v
[Supervisor Agent] ---> [Retriever Agent] ---> [Tutor Agent]
      |                                           |
      v                                           v
[Quiz Agent] ------------------------------> [Parent Report Agent]
```

## AMD MI300X Usage
This project targets **AMD Developer Cloud MI300X** by using a **vLLM OpenAI-compatible endpoint**.  
Configure the LLM endpoint via environment variables:
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

Example MI300X vLLM base URL:
```
https://<your-mi300x-endpoint>/v1
```

## Local Setup
```bash
git clone <your-repo>
cd pathshala-ai
cp .env.example .env
docker-compose up --build
```

Backend: http://localhost:8000  
Frontend: http://localhost:8501

## Demo Script
1. Upload a Nepali or English textbook PDF.
2. Ask a simple question (e.g., “What is photosynthesis?”).
3. If confused, type “I don’t समझे” to trigger Nepali explanation.
4. Review the generated quiz.
5. Open the parent summary for the student.

## Future Roadmap
- WhatsApp integration for rural families
- Full multi-subject support (Math, Science, Social Studies)
- Student voice inputs and audio explanations
- Offline/low-bandwidth mode