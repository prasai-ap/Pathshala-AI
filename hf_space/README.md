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

For scanned PDF OCR and persistent progress, deploy the FastAPI backend separately and add a Space variable named `BACKEND_URL`.
