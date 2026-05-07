import json
import os
from functools import lru_cache

from dotenv import load_dotenv
import gradio as gr
import numpy as np
import requests


load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Pathshala AI")
BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EXAMPLE_QUESTION = "mato katan bhaneko ke ho"
EXAMPLE_CONTEXT = (
    "माटो कटान भनेको पानी, हावा वा अरू कारणले माटोको माथिल्लो मलिलो भाग बग्नु हो। "
    "रूख र घाँस रोप्दा माटो जोगाउन मद्दत हुन्छ।"
)
MIN_CHUNK_CHARS = 250
MAX_CHUNK_CHARS = 900


def upload_textbook(pdf_path):
    if not pdf_path:
        return "Choose a PDF first.", "{}", gr.update()

    if BACKEND_URL:
        backend_result = upload_to_backend(pdf_path)
        if backend_result:
            return backend_result

    try:
        extracted = extract_pdf_text(pdf_path)
        chunks = chunk_text(extracted["text"])
        if not chunks:
            return "No readable text chunks could be created from this PDF.", "{}", gr.update()

        embeddings = embed_texts(chunks)
        state = {
            "filename": os.path.basename(pdf_path),
            "page_count": extracted["page_count"],
            "chunk_count": len(chunks),
            "chunks": chunks,
            "embeddings": embeddings.tolist(),
        }
        message = (
            f"Uploaded {state['filename']} inside this Space with "
            f"{state['page_count']} pages and {state['chunk_count']} chunks."
        )
        return message, encode_state(state), gr.update(value="")
    except Exception as exc:
        return f"Could not process uploaded PDF: {exc}", "{}", gr.update()


def upload_to_backend(pdf_path):
    try:
        with open(pdf_path, "rb") as pdf_file:
            response = requests.post(
                f"{BACKEND_URL}/upload-textbook",
                files={"file": (os.path.basename(pdf_path), pdf_file, "application/pdf")},
                timeout=900,
            )
        if not response.ok:
            return None
        result = response.json()
        message = (
            f"Uploaded {result['filename']} with {result['page_count']} pages "
            f"and {result['chunk_count']} chunks."
        )
        return message, "{}", gr.update(value="")
    except (OSError, requests.RequestException, ValueError):
        return None


def ask_tutor(question, student_id, textbook_context, textbook_state):
    question = (question or "").strip()
    student_id = (student_id or "hf-space-demo").strip()
    textbook_context = (textbook_context or "").strip()

    if not question:
        return (
            "Please type a student question.",
            "कृपया विद्यार्थीको प्रश्न लेख्नुहोस्।",
            "",
            "",
            "Waiting for a question.",
            "{}",
        )

    if BACKEND_URL:
        backend_result = ask_backend(question, student_id, textbook_context)
        if backend_result:
            return backend_result

    state = decode_state(textbook_state)
    sources = sources_from_context(textbook_context)
    if not sources and state:
        sources = retrieve_local_sources(normalize_question(question), state, limit=5)

    if not sources:
        sources = sources_from_context(EXAMPLE_CONTEXT)

    context = "\n\n".join(source["text"] for source in sources)
    english = (
        f"Interpreted question: {normalize_question(question)}\n\n"
        f"Answer from textbook context:\n{truncate(context, 700)}"
    )
    nepali = nepali_answer(normalize_question(question), context)
    quiz_questions = nepali_quiz_questions(context)
    quiz_state = {
        "quiz_questions": quiz_questions,
        "expected_answers": [source_answer(sources)] * 3,
    }
    return (
        english,
        nepali,
        format_quiz(quiz_questions),
        format_sources(sources),
        "Answered with the Hugging Face Space local PDF workflow.",
        encode_state(quiz_state),
    )


def ask_backend(question, student_id, textbook_context):
    payload = {
        "question": question,
        "student_id": student_id,
        "language_support": "English and Nepali",
    }
    if textbook_context:
        payload["textbook_context"] = textbook_context

    try:
        response = requests.post(f"{BACKEND_URL}/ask", json=payload, timeout=180)
        if not response.ok:
            return None
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    quiz_questions = data.get("quiz_questions", [])
    english = str(data.get("answer_english", "No English answer returned."))
    normalized = str(data.get("normalized_question") or "").strip()
    if normalized:
        english = f"Interpreted question: {normalized}\n\n{english}"

    quiz_state = {
        "quiz_id": data.get("quiz_id"),
        "quiz_questions": quiz_questions,
        "student_id": student_id,
    }
    return (
        english,
        str(data.get("answer_nepali", "नेपाली उत्तर प्राप्त भएन।")),
        format_quiz(quiz_questions),
        format_sources(data.get("retrieved_sources", [])),
        "Answered with the backend RAG workflow.",
        encode_state(quiz_state),
    )


def grade_quiz(answer_1, answer_2, answer_3, student_id, quiz_state):
    state = decode_state(quiz_state)

    if BACKEND_URL and state.get("quiz_id"):
        try:
            response = requests.post(
                f"{BACKEND_URL}/grade-quiz",
                json={
                    "student_id": (student_id or "hf-space-demo").strip(),
                    "quiz_id": state["quiz_id"],
                    "answers": [answer_1, answer_2, answer_3],
                },
                timeout=45,
            )
            if response.ok:
                return format_grade(response.json())
        except (requests.RequestException, ValueError):
            pass

    questions = state.get("quiz_questions", [])
    expected_answers = state.get("expected_answers", [])
    if not questions:
        return "Ask the tutor first so a quiz can be created."

    answers = [answer_1, answer_2, answer_3]
    score = 0
    lines = []
    for index, question in enumerate(questions[:3]):
        expected = str(expected_answers[index] if index < len(expected_answers) else "")
        answer = str(answers[index] if index < len(answers) else "")
        is_correct = is_answer_close(answer, expected)
        score += 1 if is_correct else 0
        lines.append(f"{'Correct' if is_correct else 'Needs practice'}: {question}")
        if not is_correct and expected:
            lines.append(f"Expected idea: {expected}")
    return f"Score: {score} / {min(len(questions), 3)}\n" + "\n".join(lines)


def parent_summary(student_id):
    if not BACKEND_URL:
        return (
            "Parent/teacher summary\n\n"
            "The student practiced with uploaded or pasted textbook context in this Space. "
            "For persistent progress, deploy the FastAPI backend and set BACKEND_URL."
        )

    try:
        response = requests.get(
            f"{BACKEND_URL}/parent-summary/{student_id or 'hf-space-demo'}",
            timeout=45,
        )
        if not response.ok:
            return "Summary failed."
        data = response.json()
    except (requests.RequestException, ValueError):
        return "Summary failed."

    strengths = "\n".join(f"- {item}" for item in data.get("strengths", []))
    weak_topics = data.get("weak_topics", [])
    weak_text = "\n".join(f"- {item}" for item in weak_topics) if weak_topics else "No weak topics recorded yet."
    return (
        f"Strengths\n{strengths}\n\n"
        f"Weak topics\n{weak_text}\n\n"
        f"Suggested next practice\n{data.get('suggested_next_practice', '')}\n\n"
        f"Encouraging note\n{data.get('encouraging_note', '')}"
    )


def extract_pdf_text(pdf_path):
    import fitz

    page_texts = []
    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        for page in document:
            text = page.get_text("text").strip()
            if text:
                page_texts.append(text)

    text = "\n\n".join(page_texts).strip()
    if not text:
        raise ValueError(
            "No selectable text found. For scanned PDFs, use backend OCR or paste a paragraph."
        )
    return {"text": text, "page_count": page_count}


def chunk_text(text):
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= MAX_CHUNK_CHARS:
            current = f"{current}\n{paragraph}".strip()
        elif len(current) >= MIN_CHUNK_CHARS:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks or ([text.strip()] if text.strip() else [])


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts):
    model = get_embedding_model()
    return np.asarray(
        model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    )


def retrieve_local_sources(question, state, limit=5):
    chunks = [str(chunk) for chunk in state.get("chunks", [])]
    embeddings = np.asarray(state.get("embeddings", []), dtype=float)
    if not chunks or embeddings.size == 0:
        return []

    query_embedding = embed_texts([question])[0]
    scores = embeddings @ query_embedding
    top_indices = np.argsort(scores)[::-1][:limit]
    return [
        {
            "score": float(scores[index]),
            "text": chunks[index],
            "metadata": {
                "filename": state.get("filename", "uploaded-textbook"),
                "chunk_index": int(index),
            },
        }
        for index in top_indices
    ]


def sources_from_context(text):
    chunks = chunk_text(text)
    return [
        {
            "score": 1.0,
            "text": chunk,
            "metadata": {"filename": "pasted-context", "chunk_index": index},
        }
        for index, chunk in enumerate(chunks[:5])
    ]


def normalize_question(question):
    text = question.lower()
    if "mato" in text and "katan" in text:
        return "What is soil erosion?"
    if "prakash" in text and "sansleshan" in text:
        return "What is photosynthesis?"
    if "bhinn" in text or "fraction" in text:
        return "What is a fraction?"
    return question


def nepali_answer(question, context):
    text = f"{question} {context}".lower()
    if "soil erosion" in text or "माटो कटान" in context:
        return (
            "माटो कटान भनेको पानी, हावा वा अरू कारणले माटोको माथिल्लो मलिलो भाग "
            "बग्नु वा हट्नु हो। यसले जमिनको उर्वर शक्ति घटाउँछ। रूख, घाँस र बिरुवा "
            "रोप्दा माटो जोगाउन मद्दत हुन्छ।"
        )
    if "photosynthesis" in text or "प्रकाश संश्लेषण" in context:
        return (
            "प्रकाश संश्लेषण भनेको हरिया बिरुवाले घामको प्रकाश, पानी र कार्बन "
            "डाइअक्साइड प्रयोग गरेर खाना बनाउने प्रक्रिया हो। यस क्रममा अक्सिजन पनि निस्कन्छ।"
        )
    if has_devanagari(context):
        return "अपलोड गरिएको पाठ्यपुस्तकको सन्दर्भअनुसार मुख्य कुरा यस्तो छ:\n\n" + truncate(context, 700)
    return (
        "अपलोड गरिएको पाठ्यपुस्तकको सन्दर्भअनुसार यो विषय महत्त्वपूर्ण छ। "
        "मुख्य शब्दहरू पढेर आफ्नै सरल शब्दमा उत्तर लेख्ने अभ्यास गर्नुहोस्।"
    )


def nepali_quiz_questions(context):
    short_context = truncate(first_sentence(context), 140)
    return [
        "प्राप्त पाठ्यपुस्तक सन्दर्भको मुख्य कुरा के हो?",
        f"यो वाक्यले के बुझाउँछ: {short_context}",
        "यस विषयलाई आफ्नै सरल शब्दमा कसरी भन्न सकिन्छ?",
    ]


def source_answer(sources):
    if not sources:
        return "पाठ्यपुस्तकको मुख्य कुरा।"
    text = str(sources[0].get("text", "")).strip()
    return truncate(first_sentence(text) or text, 220)


def first_sentence(text):
    for separator in ["।", ".", "?", "!"]:
        if separator in text:
            return text.split(separator, 1)[0].strip() + separator
    return text.strip()


def has_devanagari(text):
    return any("\u0900" <= character <= "\u097f" for character in text)


def is_answer_close(student_answer, expected_answer):
    student = normalize_answer(student_answer)
    expected = normalize_answer(expected_answer)
    if not student or not expected:
        return False
    student_tokens = set(student.split())
    expected_tokens = set(expected.split())
    overlap = len(student_tokens & expected_tokens) / max(len(expected_tokens), 1)
    return overlap >= 0.35 or student in expected or expected in student


def normalize_answer(answer):
    return " ".join(
        word.strip(".,?!:;()[]{}\"'।").lower()
        for word in str(answer).split()
        if word.strip(".,?!:;()[]{}\"'।")
    )


def format_quiz(questions):
    clean_questions = [str(question).strip() for question in questions if str(question).strip()]
    return "\n".join(
        f"{index}. {question}" for index, question in enumerate(clean_questions[:3], start=1)
    )


def format_sources(sources):
    if not sources:
        return "No retrieved sources returned."
    formatted = []
    for source in sources[:5]:
        metadata = source.get("metadata", {}) if isinstance(source, dict) else {}
        filename = metadata.get("filename", "textbook")
        chunk_index = metadata.get("chunk_index", "unknown")
        score = float(source.get("score", 0)) if isinstance(source, dict) else 0
        text = str(source.get("text", "")).strip() if isinstance(source, dict) else ""
        formatted.append(f"Source: {filename}, chunk {chunk_index}, score {score:.3f}\n{text}")
    return "\n\n".join(formatted)


def format_grade(data):
    lines = [f"Score: {data.get('score', 0)} / {data.get('total', 0)}"]
    for item in data.get("results", []):
        status = "Correct" if item.get("is_correct") else "Needs practice"
        lines.append(f"{status}: {item.get('question', '')}")
        if not item.get("is_correct"):
            lines.append(f"Expected idea: {item.get('expected_answer', '')}")
    return "\n".join(lines)


def encode_state(state):
    return json.dumps(state, ensure_ascii=False)


def decode_state(state):
    if isinstance(state, dict):
        return state
    if not state:
        return {}
    try:
        decoded = json.loads(str(state))
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def truncate(text, max_length):
    text = str(text)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


with gr.Blocks(title=APP_NAME, theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # Pathshala AI
        Upload a textbook PDF, ask a question, and get textbook-grounded bilingual help.
        """
    )

    textbook_state = gr.State("{}")
    quiz_state = gr.State("{}")

    with gr.Row():
        student_id_input = gr.Textbox(label="Student ID", value="hf-space-demo")
        status_output = gr.Textbox(
            label="Status",
            value=(
                "Backend connected." if BACKEND_URL else
                "Space-local PDF upload is active. Set BACKEND_URL for full backend OCR/progress."
            ),
            interactive=False,
        )

    with gr.Tab("Ask"):
        with gr.Row():
            with gr.Column():
                pdf_input = gr.File(
                    label="Upload textbook or worksheet PDF",
                    file_types=[".pdf"],
                    type="filepath",
                )
                upload_button = gr.Button("Upload PDF")
                upload_output = gr.Textbox(label="Upload result", lines=3, interactive=False)
                question_input = gr.Textbox(
                    label="Student question",
                    value=EXAMPLE_QUESTION,
                    lines=2,
                )
                context_input = gr.Textbox(
                    label="Optional textbook context",
                    value=EXAMPLE_CONTEXT,
                    lines=6,
                )
                ask_button = gr.Button("Ask Tutor", variant="primary")
            with gr.Column():
                english_output = gr.Textbox(label="English explanation", lines=8)
                nepali_output = gr.Textbox(label="Nepali explanation", lines=8)
                quiz_output = gr.Textbox(label="3 quiz questions", lines=5)
        sources_output = gr.Textbox(label="Retrieved sources", lines=8)

    with gr.Tab("Quiz"):
        answer_1 = gr.Textbox(label="Your answer 1")
        answer_2 = gr.Textbox(label="Your answer 2")
        answer_3 = gr.Textbox(label="Your answer 3")
        grade_button = gr.Button("Submit Quiz Answers", variant="primary")
        grade_output = gr.Textbox(label="Quiz result", lines=10)

    with gr.Tab("Parent Summary"):
        summary_button = gr.Button("Show Parent/Teacher Summary")
        summary_output = gr.Textbox(label="Summary", lines=10)

    upload_button.click(
        fn=upload_textbook,
        inputs=[pdf_input],
        outputs=[upload_output, textbook_state, context_input],
        api_name=False,
    )
    ask_button.click(
        fn=ask_tutor,
        inputs=[question_input, student_id_input, context_input, textbook_state],
        outputs=[
            english_output,
            nepali_output,
            quiz_output,
            sources_output,
            status_output,
            quiz_state,
        ],
        api_name=False,
    )
    grade_button.click(
        fn=grade_quiz,
        inputs=[answer_1, answer_2, answer_3, student_id_input, quiz_state],
        outputs=[grade_output],
        api_name=False,
    )
    summary_button.click(
        fn=parent_summary,
        inputs=[student_id_input],
        outputs=[summary_output],
        api_name=False,
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        prevent_thread_lock=True,
    )
    import time

    while True:
        time.sleep(60)
