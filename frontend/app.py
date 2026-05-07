import os

from dotenv import load_dotenv
import requests
import streamlit as st


load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Pathshala AI")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
HF_SPACE_URL = "https://huggingface.co/spaces/lablab-ai-amd-developer-hackathon/pathshala-ai"
UPLOAD_TIMEOUT_SECONDS = 3600
ASK_TIMEOUT_SECONDS = 180
SHORT_TIMEOUT_SECONDS = 45


def is_displayable_quiz_question(text: str) -> bool:
    cleaned = str(text or "").strip()

    if not cleaned:
        return False

    lowered = cleaned.lower()
    if lowered in {"json", "{", "}", "[", "]", "```", "```json"}:
        return False

    if cleaned.startswith(("{", "}", "[", "]")):
        return False

    return True


st.set_page_config(page_title=APP_NAME, page_icon="PA", layout="centered")

st.title(APP_NAME)
st.write(
    "A bilingual AI tutor for rural primary education in Nepal, designed to support "
    "students, teachers, and parents with simple curriculum-grounded learning help."
)
st.link_button("Open Hugging Face Space demo", HF_SPACE_URL)

student_id = st.text_input("Student ID", value="demo-student")

st.header("Upload")
uploaded_pdf = st.file_uploader("Upload textbook or worksheet PDF", type=["pdf"])

if uploaded_pdf is not None:
    if st.button("Upload PDF"):
        try:
            response = requests.post(
                f"{BACKEND_URL}/upload-textbook",
                files={"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")},
                timeout=UPLOAD_TIMEOUT_SECONDS,
            )

            if response.ok:
                result = response.json()
                st.success(
                    f"Uploaded {result['filename']} with {result['page_count']} pages "
                    f"and {result['chunk_count']} chunks."
                )
                extraction_method = result.get("extraction_method")
                if extraction_method:
                    st.caption(f"Text extraction: {extraction_method}")
            else:
                try:
                    detail = response.json().get("detail", "Upload failed.")
                except ValueError:
                    detail = "Upload failed."
                st.error(detail)
        except requests.Timeout:
            st.error(
                "Backend is still processing the PDF. Try again in a moment, or use a "
                "smaller PDF for the demo."
            )
        except requests.RequestException as exc:
            st.error(f"Could not reach backend: {exc}")

st.header("Question")
question = st.text_area("Ask a question in Nepali, romanized Nepali, or English")

if st.button("Ask Tutor", disabled=not question.strip()):
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={
                "question": question,
                "student_id": student_id,
                "language_support": "English and Nepali",
            },
            timeout=ASK_TIMEOUT_SECONDS,
        )

        if response.ok:
            st.session_state["tutor_response"] = response.json()
        else:
            try:
                detail = response.json().get("detail", "Question failed.")
            except ValueError:
                detail = "Question failed."
            st.error(detail)
    except requests.Timeout:
        st.error(
            "The tutor request timed out. If the AMD endpoint is slow or unavailable, "
            "clear LLM_BASE_URL in .env to use mock mode."
        )
    except requests.RequestException as exc:
        st.error(f"Could not reach backend: {exc}")

result = st.session_state.get("tutor_response")

st.header("Answer")
if result:
    normalized_question = result.get("normalized_question")
    if normalized_question and normalized_question.strip().lower() != question.strip().lower():
        st.caption(f"Interpreted question: {normalized_question}")

    st.subheader("English")
    st.write(result.get("answer_english", ""))

    st.subheader("Nepali")
    st.write(result.get("answer_nepali", ""))
else:
    st.info("Ask a question after uploading a textbook to see a grounded answer.")

st.header("Quiz")
if result:
    quiz_questions = [
        quiz_question
        for quiz_question in result.get("quiz_questions", [])
        if is_displayable_quiz_question(quiz_question)
    ]
    quiz_answers = []

    for index, quiz_question in enumerate(quiz_questions, start=1):
        st.write(f"{index}. {quiz_question}")
        quiz_answers.append(
            st.text_input(
                f"Your answer {index}",
                key=f"quiz_answer_{result.get('quiz_id', 'latest')}_{index}",
            )
        )

    if st.button("Submit Quiz Answers", disabled=not result.get("quiz_id")):
        try:
            response = requests.post(
                f"{BACKEND_URL}/grade-quiz",
                json={
                    "student_id": student_id,
                    "quiz_id": result.get("quiz_id"),
                    "answers": quiz_answers,
                },
                timeout=SHORT_TIMEOUT_SECONDS,
            )

            if response.ok:
                st.session_state["quiz_grade"] = response.json()
                st.success("Quiz graded.")
            else:
                try:
                    detail = response.json().get("detail", "Quiz grading failed.")
                except ValueError:
                    detail = "Quiz grading failed."
                st.error(detail)
        except requests.Timeout:
            st.error("Quiz grading timed out. Please try again.")
        except requests.RequestException as exc:
            st.error(f"Could not reach backend: {exc}")
else:
    st.info("Practice questions will appear here.")

grade = st.session_state.get("quiz_grade")

if grade:
    st.subheader("Quiz Result")
    st.write(f"Score: {grade.get('score', 0)} / {grade.get('total', 0)}")

    weak_areas = grade.get("weak_areas", [])
    if weak_areas:
        st.write(f"Weak areas: {', '.join(weak_areas)}")

    for item in grade.get("results", []):
        status = "Correct" if item.get("is_correct") else "Needs practice"
        st.write(f"{status}: {item.get('question', '')}")
        if not item.get("is_correct"):
            st.caption(f"Expected idea: {item.get('expected_answer', '')}")

st.header("Retrieved Sources")
if result:
    for match in result.get("retrieved_sources", []):
        score = match.get("score", 0)
        metadata = match.get("metadata", {})
        chunk_index = metadata.get("chunk_index", "unknown")
        filename = metadata.get("filename", "textbook")
        st.write(f"Source: {filename}, chunk {chunk_index}, score {score:.3f}")
        st.write(match.get("text", ""))
else:
    st.info("Relevant textbook chunks will appear here.")

st.header("Parent Summary")
if st.button("Show Parent/Teacher Summary"):
    try:
        response = requests.get(
            f"{BACKEND_URL}/parent-summary/{student_id}",
            timeout=SHORT_TIMEOUT_SECONDS,
        )

        if response.ok:
            st.session_state["parent_summary"] = response.json()
        else:
            try:
                detail = response.json().get("detail", "Summary failed.")
            except ValueError:
                detail = "Summary failed."
            st.error(detail)
    except requests.Timeout:
        st.error("Summary request timed out. Please try again.")
    except requests.RequestException as exc:
        st.error(f"Could not reach backend: {exc}")

summary = st.session_state.get("parent_summary")

if summary:
    st.subheader("Strengths")
    for strength in summary.get("strengths", []):
        st.write(f"- {strength}")

    st.subheader("Weak Topics")
    weak_topics = summary.get("weak_topics", [])
    if weak_topics:
        for topic in weak_topics:
            st.write(f"- {topic}")
    else:
        st.write("No weak topics recorded yet.")

    st.subheader("Suggested Next Practice")
    st.write(summary.get("suggested_next_practice", ""))

    st.subheader("Encouraging Note")
    st.write(summary.get("encouraging_note", ""))

    st.caption(
        f"Questions asked: {summary.get('questions_asked', 0)} | "
        f"Language support: {', '.join(summary.get('language_support_used', [])) or 'none yet'}"
    )
else:
    st.info("Parent-friendly learning summary will appear here.")
