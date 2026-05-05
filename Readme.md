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

---

## PDF Ingestion & Chunking ✅

### Implementation Details

**PDF Upload Endpoint** - `POST /upload-textbook`
- Accepts PDF file uploads with validation
- Extracts text using PyMuPDF
- Returns upload ID and chunk statistics

**Text Extraction** (PyMuPDF)
- Extracts text from all pages
- Handles corrupted PDFs with error messages
- Validates content is readable

**Smart Chunking**
- Splits into 512-character chunks
- Maintains 64-character overlap for context
- Uses sentence boundaries for natural splits

**In-Memory Storage**
- Chunks stored temporarily with upload ID
- Quick retrieval for future operations
- Preview endpoint for viewing chunks

**Streamlit UI Updates**
- File upload widget on "Upload Content" tab
- Real-time progress tracking
- Displays chunk statistics and preview
- Session management for textbook persistence

### Error Handling
✅ Invalid PDF format detection  
✅ Corrupted file handling  
✅ Empty file validation  
✅ No-readable-text detection  

### Next Phase
⏳ Qdrant vector database  
⏳ LLM embeddings  
⏳ Question answering from chunks  

---

## RAG Flow (Retrieval-Augmented Generation) — current plan

1. Upload PDFs → extract text → chunk into segments (implemented)
2. Compute embeddings for each chunk using `sentence-transformers`
3. Store vectors + metadata in Qdrant (implemented)
4. For an incoming question: compute question embedding → search Qdrant → retrieve top-k chunks
5. (Future) Pass retrieved context + prompt to LLM to generate grounded answers

This repo implements steps 1–4 so RAG pipelines can be plugged in next.


## Local Setup
```bash
git clone <your-repo>
cd pathshala-ai
cp .env.example .env
docker-compose up --build
```

Backend: http://localhost:8000  
Frontend: http://localhost:8501
API Docs: http://localhost:8000/docs

---

## API Endpoints

**POST /upload-textbook** - Upload and process PDF
```bash
curl -X POST "http://localhost:8000/upload-textbook" -F "file=@textbook.pdf"
```

**GET /textbooks/{upload_id}/preview** - Preview chunks
```bash
curl "http://localhost:8000/textbooks/upload-id/preview?chunk_count=3"
```

**GET /health** - Health check

**POST /search-context** - Search stored chunks for a question
```bash
curl -X POST "http://localhost:8000/search-context?question=What+is+photosynthesis?&top_k=5"
```
```bash
curl "http://localhost:8000/health"
```

---

## Demo Script

1. **Upload**: Go to "Upload Content" → Select a PDF file
2. **Extract**: Backend extracts text automatically
3. **Preview**: View chunks of extracted content
4. **Next Steps** (coming soon):
   - Ask questions about the content
   - Generate quizzes from topics
   - Track learning progress
   - Get parent reports

## Future Roadmap
- WhatsApp integration for rural families
- Full multi-subject support (Math, Science, Social Studies)
- Student voice inputs and audio explanations
- Offline/low-bandwidth mode