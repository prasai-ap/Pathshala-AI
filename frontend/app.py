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

if st.button("Find Context", disabled=not question.strip()):
    try:
        response = requests.get(
            f"{BACKEND_URL}/debug/search-context",
            params={"question": question, "limit": 3},
            timeout=30,
        )

        if response.ok:
            st.session_state["context_matches"] = response.json().get("matches", [])
        else:
            try:
                detail = response.json().get("detail", "Context search failed.")
            except ValueError:
                detail = "Context search failed."
            st.error(detail)
    except requests.RequestException as exc:
        st.error(f"Could not reach backend: {exc}")

st.header("Answer")
st.info("LLM answer is not enabled yet. Retrieved context will appear below.")

for match in st.session_state.get("context_matches", []):
    score = match.get("score", 0)
    metadata = match.get("metadata", {})
    chunk_index = metadata.get("chunk_index", "unknown")
    filename = metadata.get("filename", "textbook")
    st.write(f"Source: {filename}, chunk {chunk_index}, score {score:.3f}")
    st.write(match.get("text", ""))

st.header("Quiz")
st.info("Practice quiz will appear here.")

st.header("Parent Summary")
st.info("Parent-friendly learning summary will appear here.")
