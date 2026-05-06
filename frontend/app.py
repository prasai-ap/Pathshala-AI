import os

from dotenv import load_dotenv
import requests
import streamlit as st


load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Pathshala AI")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title=APP_NAME, page_icon="PA", layout="centered")

st.title(APP_NAME)
st.write(
    "A bilingual AI tutor for rural primary education in Nepal, designed to support "
    "students, teachers, and parents with simple curriculum-grounded learning help."
)

student_id = st.text_input("Student ID", value="demo-student")

st.header("Upload")
uploaded_pdf = st.file_uploader("Upload textbook or worksheet PDF", type=["pdf"])

if uploaded_pdf is not None:
    if st.button("Upload PDF"):
        try:
            response = requests.post(
                f"{BACKEND_URL}/upload-textbook",
                files={"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")},
                timeout=30,
            )

            if response.ok:
                result = response.json()
                st.success(
                    f"Uploaded {result['filename']} with {result['page_count']} pages "
                    f"and {result['chunk_count']} chunks."
                )
            else:
                try:
                    detail = response.json().get("detail", "Upload failed.")
                except ValueError:
                    detail = "Upload failed."
                st.error(detail)
        except requests.RequestException as exc:
            st.error(f"Could not reach backend: {exc}")

st.header("Question")
question = st.text_area("Ask a question in Nepali or English")

if st.button("Ask Tutor", disabled=not question.strip()):
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={
                "question": question,
                "student_id": student_id,
                "language_support": "English and Nepali",
            },
            timeout=90,
        )

        if response.ok:
            st.session_state["tutor_response"] = response.json()
        else:
            try:
                detail = response.json().get("detail", "Question failed.")
            except ValueError:
                detail = "Question failed."
            st.error(detail)
    except requests.RequestException as exc:
        st.error(f"Could not reach backend: {exc}")

result = st.session_state.get("tutor_response")

st.header("Answer")
if result:
    st.subheader("English")
    st.write(result.get("answer_english", ""))

    st.subheader("Nepali")
    st.write(result.get("answer_nepali", ""))
else:
    st.info("Ask a question after uploading a textbook to see a grounded answer.")

st.header("Quiz")
if result:
    quiz_questions = result.get("quiz_questions", [])

    for index, quiz_question in enumerate(quiz_questions, start=1):
        st.write(f"{index}. {quiz_question}")
else:
    st.info("Practice questions will appear here.")

st.subheader("Submit Quiz Result")
quiz_topic = st.text_input("Quiz topic", value="")
quiz_score = st.number_input("Score", min_value=0, value=0, step=1)
quiz_total = st.number_input("Total questions", min_value=1, value=3, step=1)
weak_areas_text = st.text_input("Weak areas, comma separated", value="")

if st.button("Submit Quiz Result", disabled=not quiz_topic.strip()):
    weak_areas = [
        area.strip()
        for area in weak_areas_text.split(",")
        if area.strip()
    ]

    try:
        response = requests.post(
            f"{BACKEND_URL}/submit-quiz",
            json={
                "student_id": student_id,
                "topic": quiz_topic,
                "score": quiz_score,
                "total": quiz_total,
                "weak_areas": weak_areas,
            },
            timeout=30,
        )

        if response.ok:
            st.success("Quiz result saved.")
        else:
            try:
                detail = response.json().get("detail", "Quiz submission failed.")
            except ValueError:
                detail = "Quiz submission failed."
            st.error(detail)
    except requests.RequestException as exc:
        st.error(f"Could not reach backend: {exc}")

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
            timeout=30,
        )

        if response.ok:
            st.session_state["parent_summary"] = response.json()
        else:
            try:
                detail = response.json().get("detail", "Summary failed.")
            except ValueError:
                detail = "Summary failed."
            st.error(detail)
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
