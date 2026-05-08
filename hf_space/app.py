import base64
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
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "mock").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OCR_PROVIDER = os.getenv("OCR_PROVIDER", "off").strip().lower()
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "5") or "5")
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
MIN_TEXT_CHARACTERS_FOR_DIRECT_EXTRACTION = 300


def upload_textbook(pdf_path):
    if not pdf_path:
        return "Choose a PDF first.", "{}", gr.update()

    if BACKEND_URL:
        backend_result = upload_to_backend(pdf_path)
        if backend_result:
            return backend_result

    try:
        extracted = extract_pdf_text(pdf_path)
        if is_garbled_pdf_text(extracted["text"]):
            return (
                "This PDF has a broken custom-font text layer, so the extracted text "
                "is not readable Nepali. Use the backend with Gemini OCR enabled, "
                "upload a Unicode Nepali PDF, or paste a readable lesson paragraph "
                "into the context box.",
                "{}",
                gr.update(),
            )

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
        if extracted.get("extraction_method"):
            message = f"{message} Text extraction: {extracted['extraction_method']}."
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

    normalized_question = normalize_question(question)
    context = "\n\n".join(source["text"] for source in sources)
    english_answer = generate_english_answer(normalized_question, sources)
    english = f"Interpreted question: {normalized_question}\n\n{english_answer}"
    nepali = adapt_nepali_answer(question, english_answer, sources)
    quiz_questions = nepali_quiz_questions(context)
    quiz_state = {
        "quiz_questions": quiz_questions,
        "expected_answers": [source_answer(sources)] * 3,
        "topic": display_topic(normalized_question),
        "question": question,
        "score": None,
        "total": 3,
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


def generate_english_answer(question, sources):
    if not sources:
        return "I do not have enough textbook context to answer this question."

    if not LLM_BASE_URL:
        return fallback_english_answer(sources)

    system_prompt = (
        "You are a primary-school tutor. Use only the provided textbook context. "
        "Write the answer in simple English. Keep the explanation short. Explain "
        "the idea in your own words instead of copying long textbook lines. Ignore "
        "OCR artifacts, broken words, page numbers, and source labels. If the "
        "context is insufficient, say that you do not have enough textbook context."
    )
    prompt = (
        f"Student question:\n{question}\n\n"
        f"Textbook context:\n{format_sources_for_prompt(sources)}\n\n"
        "Answer the student's question directly in 2 to 4 simple sentences."
    )

    try:
        return complete_with_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=450,
        )
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return fallback_english_answer(sources)


def complete_with_llm(prompt, system_prompt="", temperature=0.2, max_tokens=512):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    response = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        headers=headers,
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    return str(data["choices"][0]["message"]["content"]).strip()


def adapt_nepali_answer(question, english_answer, sources):
    if TRANSLATION_PROVIDER == "gemini" and GEMINI_API_KEY:
        try:
            translated = translate_with_gemini(question, english_answer)
            translated = remove_source_lines(translated)
            if is_valid_nepali(translated):
                return translated
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            pass

    if TRANSLATION_PROVIDER == "openai" and OPENAI_API_KEY:
        try:
            translated = translate_with_openai(question, english_answer)
            translated = remove_source_lines(translated)
            if is_valid_nepali(translated):
                return translated
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            pass

    return nepali_answer(
        question,
        " ".join(str(source.get("text", "")) for source in sources),
    )


def translate_with_gemini(question, english_answer):
    prompt = (
        "Translate and simplify this grounded English tutoring answer into natural "
        "Nepali for a primary-school student in Nepal. Keep the same meaning. "
        "Use Nepali Devanagari only. Do not add new facts. Do not include source "
        "citations or headings.\n\n"
        f"Student question:\n{question}\n\n"
        f"English answer:\n{english_answer}"
    )
    return gemini_generate_text(prompt, temperature=0.1, max_output_tokens=450)


def translate_with_openai(question, english_answer):
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You adapt English tutoring answers into natural Nepali for "
                        "primary-school students. Write only Nepali Devanagari. Do not "
                        "add source labels, markdown, or English sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Translate and simplify this grounded English tutoring answer "
                        "into natural Nepali for a primary-school student in Nepal. "
                        "Keep the same meaning. Use Nepali Devanagari only. Do not add "
                        "new facts. Do not include source citations or headings.\n\n"
                        f"Student question:\n{question}\n\n"
                        f"English answer:\n{english_answer}"
                    ),
                },
            ],
            "temperature": 0.1,
            "max_tokens": 450,
        },
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def normalize_with_gemini(question):
    prompt = (
        "Convert this student question into one clear, simple English question for "
        "textbook search. The question may be written in English, Nepali Devanagari, "
        "or romanized Nepali typed with English letters. Do not answer the question. "
        "Return only the rewritten English question.\n\n"
        f"Student question:\n{question}"
    )
    normalized = gemini_generate_text(prompt, temperature=0, max_output_tokens=80)
    normalized = normalized.strip().strip("\"'`").splitlines()[0].strip()
    if normalized and "?" not in normalized and len(normalized.split()) > 1:
        normalized = f"{normalized}?"
    if len(normalized) > 180 or len(normalized.strip("?").split()) < 3:
        return ""
    return normalized


def gemini_generate_text(prompt, temperature=0.1, max_output_tokens=450, parts=None):
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )
    content_parts = parts or [{"text": prompt}]
    response = requests.post(
        endpoint,
        json={
            "contents": [{"parts": content_parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        },
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def fallback_english_answer(sources):
    context = str(sources[0].get("text", "")).strip()
    if not context:
        return "I do not have enough textbook context to answer this question."

    topic_text = " ".join(str(source.get("text", "")) for source in sources[:3]).lower()
    concept_answer = known_english_concept_answer(topic_text)
    if concept_answer:
        return concept_answer

    return "Based on the textbook context, here is the simple explanation: " + truncate(
        " ".join(context.split()),
        500,
    )


def known_english_concept_answer(text):
    if (
        "living thing" in text
        or "living things" in text
        or "organism" in text
        or "organisms" in text
    ):
        return (
            "Living things are organisms that show the signs of life. They need food "
            "or energy, breathe or exchange gases, grow, respond to their surroundings, "
            "and can reproduce. Plants, animals, fungi, and microorganisms are "
            "examples of living things."
        )

    if "reflection" in text or "mirror" in text or "image of that object" in text:
        return (
            "Reflection of light means light bounces back after hitting a surface. "
            "A mirror reflects light in an orderly way, so we can see a clear image "
            "of an object in it. Smooth, flat surfaces make clearer reflections, while "
            "rough surfaces scatter light and do not show a clear image."
        )

    if "soil erosion" in text or "erosion" in text:
        return (
            "Soil erosion means the top fertile layer of soil is carried away by "
            "water, wind, or other causes. It makes land less useful for growing "
            "plants, so protecting soil with plants and controlled water flow is important."
        )

    if "photosynthesis" in text or "chlorophyll" in text:
        return (
            "Photosynthesis is the process by which green plants make their own food "
            "using sunlight, water, and carbon dioxide. Chlorophyll in leaves helps "
            "plants capture sunlight, and oxygen is released during the process."
        )

    return None


def format_sources_for_prompt(sources):
    formatted = []
    for index, source in enumerate(sources, start=1):
        metadata = source.get("metadata", {})
        filename = metadata.get("filename", "textbook")
        chunk_index = metadata.get("chunk_index", "unknown")
        formatted.append(
            f"[Source {index}: {filename}, chunk {chunk_index}]\n{source.get('text', '')}"
        )
    return "\n\n".join(formatted)


def is_valid_nepali(text):
    devanagari_count = sum(1 for character in text if "\u0900" <= character <= "\u097f")
    latin_count = sum(1 for character in text if character.isascii() and character.isalpha())
    if devanagari_count < 20 or latin_count > 12:
        return False
    forbidden_markers = ["source", "student question", "english answer", "external"]
    return not any(marker in text.lower() for marker in forbidden_markers)


def remove_source_lines(text):
    lines = []
    for line in str(text).splitlines():
        lowered = line.lower()
        if "source" in lowered or "स्रोत:" in line:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


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
                data = response.json()
                state["score"] = data.get("score")
                state["total"] = data.get("total")
                state["weak_topics"] = data.get("weak_areas", [])
                return format_grade(data), encode_state(state)
        except (requests.RequestException, ValueError):
            pass

    questions = state.get("quiz_questions", [])
    expected_answers = state.get("expected_answers", [])
    if not questions:
        return "Ask the tutor first so a quiz can be created.", encode_state(state)

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

    state["score"] = score
    state["total"] = min(len(questions), 3)
    state["last_result"] = f"Score: {score} / {min(len(questions), 3)}"
    state["weak_topics"] = [] if score >= state["total"] else [state.get("topic", "मुख्य पाठ")]
    return f"Score: {score} / {min(len(questions), 3)}\n" + "\n".join(lines), encode_state(state)


def parent_summary(student_id, quiz_state):
    if not BACKEND_URL:
        state = decode_state(quiz_state)
        topic = state.get("topic") or "आजको पाठ"
        score = state.get("score")
        total = state.get("total") or 3
        question = state.get("question") or "पाठ्यपुस्तकको प्रश्न"

        if score is None:
            return (
                "Parent/teacher summary\n\n"
                f"विद्यार्थीले {question} बारे प्रश्न सोधेको छ। अझै क्विज पेश गरिएको छैन। "
                "उत्तर पढेपछि ३ वटा छोटा प्रश्न प्रयास गराउनुहोस्।"
            )

        if score >= max(total - 1, 1):
            strength = f"{topic} को मुख्य विचार राम्रोसँग समात्दैछ।"
            weak = "अहिले कुनै स्पष्ट कमजोर क्षेत्र देखिएको छैन।"
            next_step = f"{topic} बाट अर्को उदाहरण वा अभ्यास प्रश्न गराउनुहोस्।"
            note = "विद्यार्थीले राम्रो प्रगति देखाएको छ। छोटो दैनिक अभ्यास जारी राख्नुहोस्।"
        elif score > 0:
            strength = "विद्यार्थीले केही मुख्य कुरा बुझ्न थालेको छ।"
            weak = f"{topic} का परिभाषा, मुख्य शब्द, र उदाहरण अझै अभ्यास गर्नुपर्छ।"
            next_step = f"{topic} को पाठ फेरि पढेर सजिलो उदाहरणसहित ३ छोटा प्रश्न गराउनुहोस्।"
            note = "विद्यार्थी प्रयासरत छ। गलत भएका प्रश्नलाई उदाहरणसँग जोडेर दोहोर्‍याउँदा सुधार हुन्छ।"
        else:
            strength = "विद्यार्थीले प्रश्न सोधेर अभ्यास सुरु गरेको छ।"
            weak = f"{topic} को आधारभूत अर्थ र मुख्य शब्दहरू फेरि बुझाउनुपर्छ।"
            next_step = f"{topic} को छोटो परिभाषा, चित्र/उदाहरण, र एक-एक गरी प्रश्न अभ्यास गराउनुहोस्।"
            note = "अहिले थप सहारा चाहिन्छ, तर नियमित सानो अभ्यासले सुधार ल्याउँछ।"

        return (
            "Parent/teacher summary\n\n"
            f"Quiz score: {score} / {total}\n\n"
            f"Strength\n{strength}\n\n"
            f"Needs practice\n{weak}\n\n"
            f"Suggested next practice\n{next_step}\n\n"
            f"Encouraging note\n{note}"
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
        if (
            len(text) >= MIN_TEXT_CHARACTERS_FOR_DIRECT_EXTRACTION
            and not is_garbled_pdf_text(text)
        ):
            return {"text": text, "page_count": page_count, "extraction_method": "pymupdf"}

        ocr_text = extract_text_with_gemini_ocr(document)
        if ocr_text:
            combined_text = (
                ocr_text
                if is_garbled_pdf_text(text)
                else "\n\n".join(part for part in [text, ocr_text] if part.strip())
            )
            return {
                "text": combined_text,
                "page_count": page_count,
                "extraction_method": "gemini-ocr",
            }

        if is_garbled_pdf_text(text):
            raise ValueError(
                "The PDF text layer is not readable Unicode Nepali. Add GEMINI_API_KEY "
                "and set OCR_PROVIDER=gemini in the Space secrets, or upload a Unicode "
                "Nepali PDF."
            )

        if text:
            return {"text": text, "page_count": page_count, "extraction_method": "pymupdf-low-text"}

    raise ValueError(
        "No readable text found. For scanned PDFs, add GEMINI_API_KEY and set "
        "OCR_PROVIDER=gemini in the Space secrets, or paste a readable lesson paragraph."
    )


def extract_text_with_gemini_ocr(document):
    import fitz

    if OCR_PROVIDER != "gemini" or not GEMINI_API_KEY:
        return ""

    page_limit = document.page_count
    if OCR_MAX_PAGES > 0:
        page_limit = min(document.page_count, OCR_MAX_PAGES)

    page_texts = []
    for page_index in range(page_limit):
        page = document.load_page(page_index)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        image_data = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
        prompt = (
            "Extract all readable textbook text from this page. The text may be in "
            "Nepali Devanagari or English. Return plain text only. Preserve the original "
            "language and script. Do not translate or summarize."
        )
        try:
            page_text = gemini_generate_text(
                prompt,
                temperature=0,
                max_output_tokens=1800,
                parts=[
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_data,
                        }
                    },
                ],
            )
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            continue

        if page_text:
            page_texts.append(f"Page {page_index + 1}\n{page_text}")

    return "\n\n".join(page_texts).strip()


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


def is_garbled_pdf_text(text):
    cleaned = "".join(character for character in str(text) if not character.isspace())
    if len(cleaned) < 300:
        return False

    devanagari_count = sum(1 for character in cleaned if "\u0900" <= character <= "\u097f")
    ascii_letter_count = sum(1 for character in cleaned if character.isascii() and character.isalpha())
    suspicious_symbol_count = sum(1 for character in cleaned if character in "/\\|;:{}[]'\"`~")
    suspicious_markers = ["kf7", "lj", "cfwf", "tsnf", ";sf", "PsF", "ofsf"]
    marker_hits = sum(1 for marker in suspicious_markers if marker in text)

    devanagari_ratio = devanagari_count / len(cleaned)
    ascii_ratio = ascii_letter_count / len(cleaned)
    symbol_ratio = suspicious_symbol_count / len(cleaned)

    return (
        devanagari_ratio < 0.05
        and ascii_ratio > 0.35
        and (symbol_ratio > 0.12 or marker_hits >= 2)
    )


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
    cleaned = str(question or "").strip()
    if TRANSLATION_PROVIDER == "gemini" and GEMINI_API_KEY and cleaned:
        try:
            normalized = normalize_with_gemini(cleaned)
            if normalized:
                return normalized
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            pass

    text = cleaned.lower()
    if has_any(
        text,
        [
            "living thing",
            "living things",
            "organism",
            "organisms",
            "sajeev",
            "sajiv",
            "जीवित",
            "सजीव",
        ],
    ):
        return "What are living things?"

    if (
        "soil erosion" in text
        or "erosion" in text
        or "माटो कटान" in cleaned
        or (
            has_any(text, ["mati", "mato", "matto", "maato"])
            and has_any(text, ["katan", "katne", "katnu", "bagcha", "bagdai"])
        )
    ):
        return "What is soil erosion?"

    if has_any(text, ["oxygen", "aksijan", "akshijan", "अक्सिजन"]):
        return "What is oxygen?"

    if (
        "photosynthesis" in text
        or "प्रकाश संश्लेषण" in cleaned
        or (
            has_any(text, ["prakash", "prakaash"])
            and has_any(text, ["sansleshan", "samsleshan", "sanshleshan"])
        )
    ):
        return "What is photosynthesis?"

    if has_any(text, ["fraction", "bhinn", "vag", "bhaag", "भाग", "भिन्न"]):
        return "What is a fraction?"

    if has_any(text, ["mitochondria", "mitochondrion", "mitokondria"]):
        return "What is mitochondria?"

    if has_any(text, ["chloroplast", "kloroplast", "chlorophyll"]):
        return "What is chloroplast?"

    if has_any(text, ["cell", "koshika", "kosika", "कोषिका"]):
        return "What is a cell?"

    if has_any(text, ["energy", "urja", "oorja", "ऊर्जा"]):
        return "What is energy?"

    mixed_topic = extract_mixed_language_topic(text)
    if mixed_topic:
        return f"What is {mixed_topic}?"

    return cleaned


def has_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def extract_mixed_language_topic(text):
    markers = [
        " vaneko ",
        " bhaneko ",
        " vanya ",
        " bhanya ",
        " vanne ",
        " bhanne ",
    ]

    if not any(marker in f" {text} " for marker in markers):
        return ""

    topic = f" {text} "
    removable_phrases = [
        " vaneko ",
        " bhaneko ",
        " vanya ",
        " bhanya ",
        " vanne ",
        " bhanne ",
        " ke ho ",
        " k ho ",
        " kya ho ",
        " ho ",
        " ? ",
    ]

    for phrase in removable_phrases:
        topic = topic.replace(phrase, " ")

    topic = " ".join(topic.split()).strip(" ?.,")
    if not topic:
        return ""

    blocked_words = {"malai", "please", "explain", "bujhau", "bujhaunu", "sir", "mam"}
    topic_words = [word for word in topic.split() if word not in blocked_words]
    topic = " ".join(topic_words)

    if not topic or len(topic) > 80:
        return ""

    return topic


def display_topic(question):
    normalized = str(question).lower()
    if "living thing" in normalized or "organism" in normalized:
        return "सजीव वस्तु"
    if "reflection" in normalized:
        return "प्रकाशको परावर्तन"
    if "photosynthesis" in normalized or "prakash" in normalized:
        return "प्रकाश संश्लेषण"
    if "soil erosion" in normalized or ("mato" in normalized and "katan" in normalized):
        return "माटो कटान"
    if "fraction" in normalized or "bhinn" in normalized:
        return "भिन्न"
    if "oxygen" in normalized:
        return "अक्सिजन"
    if "mitochondria" in normalized or "mitochondrion" in normalized:
        return "माइटोकन्ड्रिया"
    if "chloroplast" in normalized:
        return "क्लोरोप्लास्ट"
    if "cell" in normalized:
        return "कोषिका"
    if "energy" in normalized:
        return "ऊर्जा"
    return str(question).strip() or "आजको पाठ"


def nepali_answer(question, context):
    text = f"{question} {context}".lower()
    known_answer = known_nepali_concept_answer(text)
    if known_answer:
        return known_answer

    if has_devanagari(context):
        return "अपलोड गरिएको पाठ्यपुस्तकको सन्दर्भअनुसार मुख्य कुरा यस्तो छ:\n\n" + truncate(context, 700)
    return (
        "अपलोड गरिएको पाठ्यपुस्तकको सन्दर्भअनुसार यो विषय महत्त्वपूर्ण छ। "
        "मुख्य शब्दहरू पढेर आफ्नै सरल शब्दमा उत्तर लेख्ने अभ्यास गर्नुहोस्।"
    )


def known_nepali_concept_answer(text):
    if (
        "living thing" in text
        or "living things" in text
        or "organism" in text
        or "organisms" in text
        or "sajeev" in text
        or "sajiv" in text
        or "सजीव" in text
        or "जीवित वस्तु" in text
    ):
        return (
            "सजीव वा जीवित वस्तु भनेको जीवनका लक्षण देखाउने वस्तु हो। सजीवले "
            "खाना वा ऊर्जा लिन्छ, सास फेर्छ, बढ्छ, वातावरणको परिवर्तनमा प्रतिक्रिया "
            "दिन्छ, र प्रजनन गर्न सक्छ। बिरुवा, जनावर, ढुसी र सूक्ष्म जीवहरू "
            "सजीवका उदाहरण हुन्।"
        )

    if "reflection" in text or "mirror" in text or "ऐना" in text or "प्रतिबिम्ब" in text:
        return (
            "प्रकाशको परावर्तन भनेको प्रकाश कुनै सतहमा ठोक्किएर फर्कनु हो। ऐनाले "
            "प्रकाशलाई राम्रोसँग फर्काउँछ, त्यसैले त्यसमा वस्तुको प्रतिबिम्ब देखिन्छ। "
            "समथर र चिल्लो सतहमा प्रतिबिम्ब प्रस्ट देखिन्छ, तर खस्रो सतहमा प्रकाश धेरै "
            "दिशामा छरिने भएकाले प्रतिबिम्ब प्रस्ट देखिँदैन।"
        )

    if "soil erosion" in text or "erosion" in text or "माटो कटान" in text:
        return (
            "माटो कटान भनेको हावा, पानी वा अन्य कारणले माटोको माथिल्लो मलिलो भाग "
            "बिस्तारै बगेर वा उडेर जानु हो। यसले खेतबारीको उर्वर शक्ति घटाउँछ। "
            "त्यसैले बिरुवा रोप्ने, घाँस जोगाउने र पानीको बहाव नियन्त्रण गर्ने काम "
            "माटो जोगाउन उपयोगी हुन्छ।"
        )

    if "oxygen" in text or "अक्सिजन" in text:
        return (
            "अक्सिजन एउटा ग्यास हो। जीवित प्राणीले सास फेर्दा अक्सिजन प्रयोग गर्छन्। "
            "कोषिकाले खाना तोडेर ऊर्जा बनाउन पनि अक्सिजनको मद्दत लिन्छ। "
            "त्यसैले अक्सिजन जीवनका लागि धेरै महत्त्वपूर्ण हुन्छ।"
        )

    if "photosynthesis" in text or "chlorophyll" in text or "प्रकाश संश्लेषण" in text:
        return (
            "प्रकाश संश्लेषण भनेको हरिया बिरुवाले घामको प्रकाश, पानी र कार्बन डाइअक्साइड "
            "प्रयोग गरेर आफ्नो खाना बनाउने प्रक्रिया हो। यो काम पातमा हुने हरियो पदार्थ "
            "क्लोरोफिलको मद्दतले हुन्छ। यस प्रक्रियामा अक्सिजन पनि निस्कन्छ।"
        )

    if "fraction" in text or "भिन्न" in text:
        return (
            "भिन्न भनेको कुनै पूर्ण वस्तुको भाग देखाउने संख्या हो। माथिको संख्या अंश हो, "
            "जसले कति भाग लिइयो भनेर देखाउँछ। तलको संख्या हर हो, जसले पूर्ण वस्तु कति "
            "बराबर भागमा बाँडिएको छ भनेर देखाउँछ।"
        )

    if "mitochondria" in text or "mitochondrion" in text:
        return (
            "माइटोकन्ड्रिया कोषिकाभित्र हुने सानो अंगक हो। यसको मुख्य काम खानाबाट ऊर्जा "
            "बनाउनु हो। त्यसैले यसलाई कोषिकाको ऊर्जा घर पनि भनिन्छ।"
        )

    if "chloroplast" in text or "plastid" in text:
        return (
            "क्लोरोप्लास्ट बिरुवाको कोषिकामा पाइने हरियो अंगक हो। यसमा क्लोरोफिल हुन्छ। "
            "क्लोरोफिलले घामको प्रकाश लिन मद्दत गर्छ र बिरुवाले खाना बनाउन सक्छ।"
        )

    if "cell" in text or "कोषिका" in text:
        return (
            "कोषिका जीवित वस्तुको सबैभन्दा सानो आधारभूत एकाइ हो। हाम्रो शरीर, बिरुवा "
            "र धेरै जीवहरू कोषिकाबाट बनेका हुन्छन्। कोषिकाले जीवनका आवश्यक कामहरू गर्छ।"
        )

    if "energy" in text or "ऊर्जा" in text:
        return (
            "ऊर्जा भनेको काम गर्न चाहिने शक्ति हो। जीवित प्राणीले खाना र सास फेर्ने "
            "प्रक्रियाबाट ऊर्जा पाउँछन्। कोषिकाले यही ऊर्जा प्रयोग गरेर जीवनका काम गर्छ।"
        )

    return None


def nepali_quiz_questions(context):
    short_context = truncate(first_sentence(context), 140)
    return [
        "प्राप्त पाठ्यपुस्तक सन्दर्भको मुख्य कुरा के हो?",
        f"यो वाक्यले के बुझाउँछ: {short_context}",
        "यस विषयलाई आफ्नै सरल नेपाली शब्दमा कसरी भन्न सकिन्छ?",
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


def startup_status():
    if BACKEND_URL:
        return "Backend connected."

    llm_status = "AMD/vLLM tutor enabled." if LLM_BASE_URL else "Local tutor fallback enabled."
    nepali_status = (
        "Gemini Nepali adaptation enabled."
        if TRANSLATION_PROVIDER == "gemini" and GEMINI_API_KEY
        else "OpenAI Nepali adaptation enabled."
        if TRANSLATION_PROVIDER == "openai" and OPENAI_API_KEY
        else "Mock Nepali adaptation enabled."
    )
    ocr_status = (
        "Gemini OCR enabled."
        if OCR_PROVIDER == "gemini" and GEMINI_API_KEY
        else "Text-based PDF extraction enabled."
    )
    return f"{llm_status} {nepali_status} {ocr_status}"


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
            value=startup_status(),
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
        outputs=[grade_output, quiz_state],
        api_name=False,
    )
    summary_button.click(
        fn=parent_summary,
        inputs=[student_id_input, quiz_state],
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
