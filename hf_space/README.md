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

## Backend Mode

Set `BACKEND_URL` to use the FastAPI backend:

```bash
BACKEND_URL=https://your-backend.example.com
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
