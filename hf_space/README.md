---
title: Pathshala AI
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# Pathshala AI

Pathshala AI is a bilingual AI tutor demo for rural primary students in Nepal.

The Gradio Space accepts a student question in English, Nepali, or romanized Nepali plus optional textbook context, then returns:

- English explanation
- Nepali explanation
- 3 simple quiz questions

## Deploy To Hugging Face Spaces

1. Create a new Hugging Face Space.
2. Choose `Gradio` as the SDK.
3. Upload the files from this `hf_space/` folder into the root of the Space:
   - `app.py`
   - `requirements.txt`
   - `README.md`
4. Commit the files. Hugging Face will build and run the Space automatically.

You can also deploy with Git:

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/pathshala-ai
cp hf_space/app.py pathshala-ai/app.py
cp hf_space/requirements.txt pathshala-ai/requirements.txt
cp hf_space/README.md pathshala-ai/README.md
cd pathshala-ai
git add .
git commit -m "Deploy Pathshala AI Gradio demo"
git push
```

## Recommended Submission Mode

For the easiest hackathon submission, deploy the Space without `BACKEND_URL`.
It will use the built-in mock fallback, so judges can try it immediately.

For the full RAG workflow, first deploy the FastAPI backend somewhere public, then set `BACKEND_URL` in the Space settings.

## Backend Mode

Set `BACKEND_URL` to use the FastAPI backend:

```bash
BACKEND_URL=https://your-backend.example.com
```

In Hugging Face Spaces, add it under:

```text
Space settings -> Variables and secrets -> New variable
```

The app calls `POST /ask` and displays the backend response.
If the backend returns `normalized_question`, the Space shows the interpreted question above the English explanation.

## Mock Mode

If `BACKEND_URL` is missing or the backend is unavailable, the Space uses a simple mock fallback so the demo remains easy to try.

Example question:

```text
soil erosion vaneko ke ho
```

You can also try mixed romanized Nepali questions such as:

```text
photosynthesis vaneko ke ho vana
```
