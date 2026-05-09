---
title: Pathshala AI
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
python_version: 3.11
pinned: false
---

# Pathshala AI

Pathshala AI is a bilingual AI tutor demo for rural primary students in Nepal.

This Hugging Face Space supports:

- Uploading a text-based PDF textbook directly in the Space
- Asking questions in English, Nepali, or romanized Nepali
- Retrieving relevant textbook portions from the uploaded PDF
- Showing a simple English answer and Nepali explanation
- Generating Nepali quiz questions
- Basic quiz grading

For the full web-app workflow, deploy the FastAPI backend separately and add a Space variable named `BACKEND_URL`.

Without `BACKEND_URL`, the Space can still run the same style of workflow locally. Add these Space secrets/variables to match the web app more closely:

- `LLM_PROVIDER=qwen`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` for the Qwen/vLLM tutor
- `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL` for the Gemini tutor
- `TRANSLATION_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL` for Nepali adaptation and romanized question normalization
- `TRANSLATION_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` if you want to use OpenAI for Nepali adaptation instead
- `OCR_PROVIDER=gemini`, `OCR_MAX_PAGES=5` for scanned or custom-font PDFs
- `DEPLOYMENT_WARNING_ENABLED=true`, `DEPLOYMENT_WARNING_MESSAGE=...` to show a visible warning when hosted credits or model services are unavailable

Use `LLM_MODEL=Qwen/Qwen3-4B-Instruct-2507` to match the project default unless your vLLM endpoint exposes a different model name. Use `GEMINI_MODEL=gemini-2.5-flash` for stable Gemini API access, or `gemini-3-flash-preview` only if that preview model is enabled for your project.
