import os

import requests
import streamlit as st


st.set_page_config(page_title="Pathshala AI", page_icon="PA", layout="centered")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("Pathshala AI")
st.write(
    "A bilingual AI tutor for rural primary education in Nepal, designed to support "
    "students, teachers, and parents with simple curriculum-grounded learning help."
)

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
            json={"question": question},
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
st.info("Parent-friendly learning summary will appear here.")
