import os
from typing import Any

import gradio as gr
import requests


BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")
EXAMPLE_QUESTION = "What is a fraction?"
EXAMPLE_CONTEXT = (
    "A fraction shows a part of a whole. The top number tells how many parts we have. "
    "The bottom number tells how many equal parts the whole is divided into."
)


def ask_tutor(question: str, textbook_context: str) -> tuple[str, str, str]:
    question = question.strip()
    textbook_context = textbook_context.strip()

    if not question:
        return (
            "Please type a student question.",
            "कृपया विद्यार्थीको प्रश्न लेख्नुहोस्।",
            "1. Add a question first.\n2. Then try again.\n3. Use a textbook topic.",
        )

    if BACKEND_URL:
        backend_result = ask_backend(question)

        if backend_result:
            return backend_result

    return mock_response(question=question, textbook_context=textbook_context)


def ask_backend(question: str) -> tuple[str, str, str] | None:
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={
                "question": question,
                "student_id": "hf-space-demo",
                "language_support": "English and Nepali",
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None
    except ValueError:
        return None

    return format_backend_response(data)


def format_backend_response(data: dict[str, Any]) -> tuple[str, str, str]:
    quiz_questions = data.get("quiz_questions", [])

    return (
        data.get("answer_english", "No English answer returned."),
        data.get("answer_nepali", "नेपाली उत्तर प्राप्त भएन।"),
        format_quiz(quiz_questions),
    )


def mock_response(question: str, textbook_context: str) -> tuple[str, str, str]:
    context = textbook_context or EXAMPLE_CONTEXT
    simple_context = truncate(context, max_length=450)

    english = (
        "Mock demo answer: I am using the textbook context only. "
        f"For the question '{question}', a simple explanation is: {simple_context}"
    )
    nepali = (
        "Mock demo उत्तर: म पाठ्यपुस्तकको सन्दर्भ मात्र प्रयोग गर्दैछु। "
        f"'{question}' प्रश्नका लागि सरल व्याख्या: {simple_context}"
    )
    quiz = format_quiz(
        [
            "What is the main idea from the explanation?",
            "Can you give one simple example?",
            "Can you explain it in your own words?",
        ]
    )

    return english, nepali, quiz


def format_quiz(quiz_questions: list[Any]) -> str:
    questions = [
        str(question).strip()
        for question in quiz_questions
        if str(question).strip()
    ]

    if not questions:
        questions = [
            "What did you learn from the explanation?",
            "Can you give one example?",
            "Can you explain it to a friend?",
        ]

    return "\n".join(
        f"{index}. {question}"
        for index, question in enumerate(questions[:3], start=1)
    )


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text

    return f"{text[: max_length - 3]}..."


with gr.Blocks(title="Pathshala AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # Pathshala AI
        Bilingual AI tutor for rural primary students in Nepal.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            question_input = gr.Textbox(
                label="Student question",
                placeholder=EXAMPLE_QUESTION,
                value=EXAMPLE_QUESTION,
                lines=2,
            )
            context_input = gr.Textbox(
                label="Optional textbook context",
                placeholder="Paste a short textbook paragraph here.",
                value=EXAMPLE_CONTEXT,
                lines=5,
            )
            ask_button = gr.Button("Ask Tutor", variant="primary")

        with gr.Column(scale=1):
            english_output = gr.Textbox(
                label="English explanation",
                lines=6,
            )
            nepali_output = gr.Textbox(
                label="Nepali explanation",
                lines=6,
            )
            quiz_output = gr.Textbox(
                label="3 quiz questions",
                lines=5,
            )

    gr.Examples(
        examples=[
            [EXAMPLE_QUESTION, EXAMPLE_CONTEXT],
        ],
        inputs=[question_input, context_input],
        outputs=[english_output, nepali_output, quiz_output],
        fn=ask_tutor,
        cache_examples=False,
    )

    ask_button.click(
        fn=ask_tutor,
        inputs=[question_input, context_input],
        outputs=[english_output, nepali_output, quiz_output],
    )


if __name__ == "__main__":
    demo.launch()
