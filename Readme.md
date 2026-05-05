# Pathshala AI 🎓

**Bilingual AI Tutor for Rural Primary Education in Nepal**

---

## Problem Statement

Rural areas in Nepal face significant educational challenges:
- Limited access to qualified teachers
- Scarcity of educational resources and materials
- Language barriers (Nepali/English)
- No personalized learning support
- Lack of parent engagement in education

Traditional education models cannot reach remote communities effectively, leaving millions of children without adequate educational support.

---

## Solution

Pathshala AI is an intelligent tutoring system that:
- Provides **24/7 personalized AI tutoring** in Nepali and English
- Enables **self-paced learning** adapted to each student's level
- Generates **progress reports for parents** to track learning
- Creates **interactive quizzes** to assess understanding
- Stores **educational content** for offline reference
- Uses **semantic search** to find relevant learning materials

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Pathshala AI System                │
├─────────────────────────────────────────────────────┤
│                                                       │
│  Frontend (Streamlit)          Backend (FastAPI)     │
│  ├─ Student Interface          ├─ Health Check      │
│  ├─ Question Input             ├─ Supervisor Agent  │
│  ├─ Quiz Interface             ├─ Tutor Agent       │
│  ├─ Parent Reports             ├─ Quiz Agent        │
│  └─ Content Upload             ├─ Retriever Agent   │
│                                ├─ Report Agent      │
│                                └─ Services          │
│                                   ├─ PDF Loader     │
│                                   ├─ Chunker        │
│                                   ├─ Vector Store   │
│                                   ├─ LLM Client     │
│                                   └─ Student Store  │
│                                                       │
│                    Infrastructure                    │
│  ┌───────────────────────────────────────────┐     │
│  │  Qdrant Vector Database (Docker)          │     │
│  │  • Document embeddings                    │     │
│  │  • Semantic search                        │     │
│  └───────────────────────────────────────────┘     │
│                                                       │
└─────────────────────────────────────────────────────┘
```

### Key Components

- **Frontend**: Streamlit web interface for students and parents
- **Backend**: FastAPI REST API with agent-based architecture
- **Vector Store**: Qdrant for semantic search on educational content
- **LLM Integration**: OpenAI/LLM for natural language understanding and generation
- **Agents**:
  - Supervisor: Routes requests to appropriate agents
  - Tutor: Answers student questions pedagogically
  - Quiz: Generates and evaluates quizzes
  - Retriever: Searches relevant educational content
  - Parent Reporter: Generates progress reports

---

## AMD MI300X Usage Plan

The AMD MI300X GPU will accelerate:
1. **Embedding Generation**: Fast vector creation for document chunking
2. **Vector Search**: Efficient Qdrant operations for content retrieval
3. **LLM Inference**: Accelerated text generation for tutoring responses
4. **Batch Processing**: Parallel processing of multiple student requests
5. **Real-time Performance**: Sub-second response times for better UX

Configuration for GPU acceleration is prepared in the `.env` file.

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