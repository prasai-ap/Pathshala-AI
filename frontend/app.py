import streamlit as st


st.set_page_config(page_title="Pathshala AI", page_icon="PA", layout="centered")

st.title("Pathshala AI")
st.write(
    "A bilingual AI tutor for rural primary education in Nepal, designed to support "
    "students, teachers, and parents with simple curriculum-grounded learning help."
)

st.header("Upload")
st.file_uploader("Upload textbook or worksheet PDF", type=["pdf"], disabled=True)
st.caption("Placeholder for curriculum upload.")

st.header("Question")
st.text_area("Ask a question in Nepali or English", disabled=True)
st.caption("Placeholder for student questions.")

st.header("Answer")
st.info("Tutor answer will appear here.")

st.header("Quiz")
st.info("Practice quiz will appear here.")

st.header("Parent Summary")
st.info("Parent-friendly learning summary will appear here.")
