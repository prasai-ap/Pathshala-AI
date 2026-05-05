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
st.text_area("Ask a question in Nepali or English", disabled=True)
st.caption("Placeholder for student questions.")

st.header("Answer")
st.info("Tutor answer will appear here.")

st.header("Quiz")
st.info("Practice quiz will appear here.")

st.header("Parent Summary")
st.info("Parent-friendly learning summary will appear here.")
