# Pathshala AI

Pathshala AI is a bilingual AI tutor for rural primary education in Nepal. It helps students ask questions in English, Nepali, or romanized Nepali, grounds answers in uploaded textbook PDFs, creates short practice quizzes, and gives parents or teachers a simple progress summary.

## Hackathon Pitch

Many rural primary students in Nepal do not have steady access to personalized learning support, bilingual explanations, or parent-friendly feedback. Pathshala AI turns a local textbook PDF into a small tutoring workflow: retrieve the right lesson context, explain it simply, ask practice questions, and summarize progress in language that families and teachers can use.

## What Works Now

- Upload a textbook or worksheet PDF.
- Extract and chunk selectable PDF text with PyMuPDF.
- Optionally use Gemini OCR for scanned Nepali or English PDF pages.
- Embed chunks with `sentence-transformers`.
- Store and search curriculum chunks with Qdrant.
- Ask a student question through `POST /ask`.
- Accept English, Nepali, and romanized Nepali questions such as `mato katan bhaneko ke ho`.
- Generate a grounded English explanation with AMD MI300X/vLLM or mock fallback.
- Adapt the English answer into natural Nepali using Gemini.
- Generate 3 simple quiz questions with hidden answer keys.
- Auto-grade quiz answers and infer weak areas from missed questions.
- Track questions asked, topics, quiz scores, weak areas, and bilingual support in memory.
- Show a parent/teacher summary.
- Run a separate Hugging Face Space demo with Gradio.

## Architecture

```text
Student / Teacher
      |
      v
Streamlit UI  --------------------->  FastAPI Backend
      |                                      |
      |                                      +--> PDF Loader
      |                                      |    - PyMuPDF text extraction
      |                                      |    - optional Gemini OCR fallback
      |                                      |    - chunk_text()
      |                                      |
      |                                      +--> Embedding Service
      |                                      |    - sentence-transformers
      |                                      |
      |                                      +--> Qdrant Vector Store
      |                                      |    - textbook chunk vectors
      |                                      |    - top-k context retrieval
      |                                      |
      |                                      +--> Agents
      |                                      |    - RetrieverAgent
      |                                      |    - TutorAgent
      |                                      |    - QuizAgent
      |                                      |
      |                                      +--> LLM Client
      |                                      |    - AMD MI300X vLLM endpoint
      |                                      |    - mock fallback for local demo
      |                                      |
      |                                      +--> Nepali Adaptation Service
      |                                      |    - Gemini, or mock fallback
      |                                      |    - romanized Nepali question normalization
      |                                      |    - language polish only
      |                                      |
      |                                      +--> StudentStore
      |                                           - in-memory progress
      |                                           - parent summary
      |
      v
English answer, Nepali answer, quiz, sources, parent summary
```

## RAG Flow

1. Upload a PDF textbook through Streamlit or `POST /upload-textbook`.
2. The backend extracts readable text. If a scanned/image PDF has too little selectable text and `OCR_PROVIDER=gemini`, it uses Gemini OCR. For demos, keep `OCR_MAX_PAGES` small, such as `5`, so upload stays fast.
3. The backend chunks the extracted text, embeds every chunk, and stores the vectors in Qdrant.
4. A student question is normalized if needed. For example, romanized Nepali like `mato katan bhaneko ke ho` is interpreted as `What is soil erosion?`.
5. The normalized question is embedded with the same sentence-transformer model.
6. `search_context(question)` retrieves the top relevant chunks. If `POST /ask` includes `textbook_context`, that provided context is used directly instead.
7. `POST /ask` sends the normalized question and textbook context through the tutoring workflow.
8. AMD MI300X/vLLM generates the core textbook-grounded English tutoring answer.
9. Gemini adapts only that English answer into natural Nepali for primary-school students.
10. The response includes `normalized_question`, `answer_english`, `answer_nepali`, `quiz_id`, `quiz_questions`, and `retrieved_sources`.
11. The UI shows only quiz questions to the student. Hidden expected answers stay in backend memory and are used by `POST /grade-quiz`.

## AMD MI300X vLLM Mode

Pathshala AI uses an OpenAI-compatible client, so it can call a vLLM server hosted on AMD Developer Cloud MI300X. The backend reads:

```env
LLM_BASE_URL=http://YOUR_AMD_CLOUD_IP:8000/v1
LLM_API_KEY=dummy
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

Expected endpoint:

```text
POST {LLM_BASE_URL}/chat/completions
```

This lets the app use high-throughput MI300X inference for core textbook-grounded reasoning while keeping local development simple. For local mock mode, leave `LLM_BASE_URL` empty so the backend returns deterministic demo responses without calling a model server.

Important: AMD MI300X/vLLM is used for core textbook-grounded reasoning. Gemini is optional support for language adaptation and scanned-PDF OCR; it does not replace the core tutor model.

At startup, backend logs clearly show one of:

- `LLM mode: AMD vLLM mode ...`
- `LLM mode: mock mode because LLM_BASE_URL is empty.`

## Nepali Language Adaptation

The AMD-hosted tutor model produces the grounded English explanation. Gemini can then help with question normalization and translation/polish into simple Nepali.

Set these values in `.env`:

```env
TRANSLATION_PROVIDER=gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash
```

For offline/local demo fallback:

```env
TRANSLATION_PROVIDER=mock
```

If `TRANSLATION_PROVIDER=gemini` but `GEMINI_API_KEY` is missing, the app falls back to mock Nepali adaptation. Provider failures also fall back to mock so the demo keeps working. The mock path includes keyword support for common romanized Nepali questions such as `oxygen ke ho`, `mato katan bhaneko ke ho`, and `prakash sansleshan vaneko ke ho`.

## Nepali PDF And OCR

Text-based Nepali PDFs are supported through PyMuPDF extraction and the multilingual embedding model. For scanned or image-based Nepali textbooks, enable Gemini OCR:

```env
OCR_PROVIDER=gemini
OCR_MAX_PAGES=5
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash
```

OCR runs only when normal PDF text extraction finds very little text or a broken custom-font text layer. `OCR_MAX_PAGES=0` means OCR every page. Whole-book OCR can take many minutes and may pause/retry when Gemini returns rate limits or temporary service errors. For a quicker demo, use a small positive number, such as `OCR_MAX_PAGES=5`. For a full production system, this should move to a dedicated OCR pipeline with background jobs, retries, caching, and stronger page-level progress reporting.

After changing `.env`, recreate the backend/frontend containers so Docker reloads the env values:

```bash
docker compose up -d --force-recreate backend frontend
```

## Environment Variables

Copy the example environment file before running locally:

```bash
cp .env.example .env
```

The app loads `.env` with `python-dotenv`. Docker Compose also reads `.env`.

| Variable | Used by | Notes |
| --- | --- | --- |
| `APP_NAME` | Backend, frontend | App title and startup logging |
| `ENVIRONMENT` | Backend | Startup logging and deployment label |
| `BACKEND_HOST` | Docker/backend | Uvicorn bind host |
| `BACKEND_PORT` | Docker/backend | Uvicorn port and host mapping |
| `BACKEND_URL` | Frontend, HF Space | API base URL |
| `FRONTEND_PORT` | Docker/frontend | Streamlit port and host mapping |
| `QDRANT_URL` | Backend | Qdrant connection URL |
| `QDRANT_API_KEY` | Backend | Required for Qdrant Cloud; leave empty for local Docker Qdrant |
| `QDRANT_COLLECTION` | Backend | Collection for textbook chunks |
| `EMBEDDING_MODEL` | Backend | sentence-transformers model name |
| `LLM_BASE_URL` | Backend | Empty means mock mode; set to AMD vLLM `/v1` URL for real inference |
| `LLM_API_KEY` | Backend | Sent as bearer token when configured |
| `LLM_MODEL` | Backend | Model name sent to `/chat/completions` |
| `TRANSLATION_PROVIDER` | Backend | `gemini` or `mock` for Nepali adaptation |
| `GEMINI_API_KEY` | Backend | Gemini key for Nepali adaptation and optional OCR |
| `GEMINI_MODEL` | Backend | Gemini model for Nepali adaptation and optional OCR |
| `OCR_PROVIDER` | Backend | `gemini` enables OCR fallback for scanned PDFs; `off` disables OCR |
| `OCR_MAX_PAGES` | Backend | `0` means OCR the whole scanned PDF; use a small positive number like `5` for fast demos |

## Local Setup

Prerequisites:

- Docker Desktop
- Git
- Optional: AMD Developer Cloud vLLM endpoint for real model responses

Create your local environment file:

```bash
cp .env.example .env
```

The default `.env.example` leaves `LLM_BASE_URL` empty so the app starts in mock LLM mode. To use AMD vLLM mode, set:

```env
LLM_BASE_URL=http://YOUR_AMD_CLOUD_IP:8000/v1
LLM_API_KEY=dummy
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

Run the full app:

```bash
docker compose up --build
```

Open:

```text
Frontend: http://localhost:8501
Backend:  http://localhost:8000
Qdrant:   http://localhost:6333
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","service":"pathshala-ai-backend"}
```

## Mock LLM Demo Mode

Mock mode is useful for judging and local demos when no AMD endpoint is running.

In your runtime environment, set:

```env
LLM_BASE_URL=
LLM_API_KEY=dummy
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

Then run the app and ask a question. The app still returns an English explanation, Nepali explanation, quiz questions, and retrieved sources, but the answer is generated by a simple fallback instead of an external model.

## Render With Qdrant Cloud

For a Render free-tier demo, use Qdrant Cloud instead of running the local `qdrant` Docker service. Set these environment variables on the Render backend web service:

```env
ENVIRONMENT=production
BACKEND_URL=https://YOUR-BACKEND-SERVICE.onrender.com
QDRANT_URL=https://YOUR-QDRANT-CLUSTER-URL
QDRANT_API_KEY=YOUR_QDRANT_CLOUD_API_KEY
QDRANT_COLLECTION=pathshala_curriculum
LLM_BASE_URL=
LLM_API_KEY=dummy
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
TRANSLATION_PROVIDER=gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash
OCR_PROVIDER=gemini
OCR_MAX_PAGES=5
```

Backend Render commands:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Frontend Render commands:

```bash
pip install -r requirements-frontend.txt
streamlit run frontend/app.py --server.address 0.0.0.0 --server.port $PORT
```

Set the frontend service `BACKEND_URL` to the public backend URL, for example `https://YOUR-BACKEND-SERVICE.onrender.com`.

### Single Render Service Option

For the simplest free-tier demo, you can run both FastAPI and Streamlit in one Render web service. Render exposes Streamlit publicly on `$PORT`, while FastAPI listens privately inside the same service on `127.0.0.1:8000`.

Use these Render settings:

```text
Runtime: Python
Build Command: pip install -r requirements.txt -r requirements-frontend.txt
Start Command: bash scripts/render-start.sh
Instance Type: Free
```

If you use the single-service start script, make sure the build command installs Streamlit. The repo also includes `streamlit` in `requirements.txt`, so `pip install -r requirements.txt` is enough, but the combined command above is still fine.

The repo includes `.python-version` with `3.11` so Render uses a Python version compatible with `sentence-transformers` and the pinned CPU PyTorch wheel. If Render has already cached a different version, set this environment variable in the Render service too:

```env
PYTHON_VERSION=3.11.11
```

Set these environment variables:

```env
APP_NAME=Pathshala AI
ENVIRONMENT=production
BACKEND_URL=http://127.0.0.1:8000
BACKEND_INTERNAL_PORT=8000

QDRANT_URL=https://YOUR-QDRANT-CLUSTER-URL
QDRANT_API_KEY=YOUR_QDRANT_CLOUD_API_KEY
QDRANT_COLLECTION=pathshala_curriculum

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

LLM_BASE_URL=
LLM_API_KEY=dummy
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct

TRANSLATION_PROVIDER=gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash

OCR_PROVIDER=gemini
OCR_MAX_PAGES=5
```

Use two separate Render services instead if you need the FastAPI backend to have its own public URL, for example for a Hugging Face Space `BACKEND_URL`.

## Troubleshooting

If Streamlit shows a message like:

```text
Could not reach backend: HTTPConnectionPool(host='backend', port=8000): Read timed out.
```

Check these first:

1. Make sure the containers are running with `docker compose ps`.
2. Check backend health at `http://localhost:8000/health`.
3. Wait for the first embedding model load to finish; the first upload or question can be slower.
4. If you are not actively using AMD Developer Cloud, set `LLM_BASE_URL=` in `.env` and restart with `docker compose up --build -d`.
5. If you run Streamlit outside Docker on your host machine, set `BACKEND_URL=http://localhost:8000` because `http://backend:8000` is only valid inside Docker Compose.
6. If the backend returns `The model ... does not exist`, keep `LLM_BASE_URL` but update `LLM_MODEL` to the exact model name served by your vLLM endpoint, or clear `LLM_BASE_URL` for mock mode.

## API Quick Test

Ask endpoint:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d "{\"student_id\":\"demo-student\",\"question\":\"What is a fraction?\",\"language_support\":\"English and Nepali\"}"
```

Submit quiz result:

```bash
curl -X POST http://localhost:8000/grade-quiz \
  -H "Content-Type: application/json" \
  -d "{\"student_id\":\"demo-student\",\"quiz_id\":\"QUIZ_ID_FROM_ASK\",\"answers\":[\"part of a whole\",\"equal parts\",\"top and bottom numbers\"]}"
```

Parent summary:

```bash
curl http://localhost:8000/parent-summary/demo-student
```

Debug retrieval:

```bash
curl "http://localhost:8000/debug/search-context?question=What%20is%20a%20fraction%3F&limit=3"
```

## Demo Script

1. Start with the problem: rural primary students need simple bilingual help grounded in their actual textbooks.
2. Open `http://localhost:8501`.
3. Upload a small textbook or worksheet PDF.
4. Ask: `mato katan bhaneko ke ho` or `What is a fraction?`
5. Show the interpreted question, English explanation, Nepali explanation, 3 quiz questions, and retrieved textbook sources.
6. Type short quiz answers and submit them. The backend auto-grades and infers weak areas.
7. Click `Show Parent/Teacher Summary`.
8. Explain that AMD MI300X vLLM can replace mock mode by setting `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
9. Explain that Gemini is enabled for language adaptation and optional scanned-PDF OCR, while AMD MI300X/vLLM handles the textbook-grounded reasoning.

## Screenshots

Add final hackathon screenshots here:

- `docs/screenshots/01-upload.png` - PDF upload and chunk indexing
- `docs/screenshots/02-question.png` - student question and bilingual answer
- `docs/screenshots/03-quiz.png` - generated quiz questions
- `docs/screenshots/04-parent-summary.png` - parent/teacher summary
- `docs/screenshots/05-hf-space.png` - Hugging Face Gradio demo

## Hugging Face Space

A Gradio demo is included in `hf_space/`.

Files:

- `hf_space/app.py`
- `hf_space/requirements.txt`
- `hf_space/README.md`

To deploy:

1. Create a new Hugging Face Space.
2. Choose Gradio as the SDK.
3. Upload the contents of `hf_space/`.
4. Optional: add a Space secret named `BACKEND_URL` pointing to a deployed backend.

If `BACKEND_URL` is missing, the Space can still upload text-based PDFs, extract text with PyMuPDF, embed chunks in memory, retrieve relevant portions, and show Nepali quiz questions. If `BACKEND_URL` is set, the Space calls the deployed FastAPI backend for the full RAG, OCR, grading, and progress workflow.

Example question:

```text
What is a fraction?
```

## Project Structure

```text
backend/
  agents/              Agent wrappers for retrieval, tutoring, quiz generation
  models/              Pydantic API schemas
  services/            PDF, embedding, Qdrant, LLM, and student progress services
  main.py              FastAPI app and endpoints
frontend/
  app.py               Streamlit interface
hf_space/
  app.py               Gradio Space demo
  requirements.txt
  README.md
docker-compose.yml     Backend, frontend, and Qdrant services
```

## Future Roadmap

1. Persist student progress in a database instead of memory.
2. Add teacher-managed classes and student profiles.
3. Add better topic extraction from textbook metadata and curriculum units.
4. Support speech input and audio explanations for early readers.
5. Add offline-first deployment for low-connectivity schools.
6. Improve Nepali evaluation with teacher feedback.
7. Add role-specific dashboards for students, teachers, and parents.
8. Add automated tests for API flows and retrieval quality.

## Notes

- Progress tracking is currently in memory and resets when the backend restarts.
- Qdrant data persists in the Docker volume `qdrant_data`.
- The frontend uses `requirements-frontend.txt` so it does not install the backend ML stack.
- The backend uses CPU PyTorch wheels for local sentence-transformers development.
