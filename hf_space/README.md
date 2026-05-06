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

The Gradio Space accepts a student question and optional textbook context, then returns:

- English explanation
- Nepali explanation
- 3 simple quiz questions

## Backend Mode

Set `BACKEND_URL` to use the FastAPI backend:

```bash
BACKEND_URL=https://your-backend.example.com
```

The app calls `POST /ask` and displays the backend response.

## Mock Mode

If `BACKEND_URL` is missing or the backend is unavailable, the Space uses a simple mock fallback so the demo remains easy to try.

Example question:

```text
What is a fraction?
```
