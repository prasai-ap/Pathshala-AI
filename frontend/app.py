"""
Pathshala AI - Streamlit Frontend
Bilingual interface for students and parents
"""
import streamlit as st
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Pathshala AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "uploaded_textbook_id" not in st.session_state:
    st.session_state.uploaded_textbook_id = None
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None

# Styling
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 10px;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# Main title
st.markdown("<h1 class='main-title'>📚 Pathshala AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Bilingual AI Tutor for Rural Primary Education</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("Navigation")
    page = st.radio("Select Page", [
        "Home",
        "Upload Content",
        "Ask Question",
        "Take Quiz",
        "Parent Report"
    ])

# Main content based on selection
if page == "Home":
    st.header("Welcome to Pathshala AI")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📖 For Students")
        st.write("""
        - Ask questions in Nepali or English
        - Get personalized tutoring explanations
        - Test your knowledge with interactive quizzes
        - Learn at your own pace
        """)
    
    with col2:
        st.subheader("👨‍👩‍👧 For Parents")
        st.write("""
        - Track your child's progress
        - Receive weekly/monthly reports
        - Understand learning patterns
        - Get improvement recommendations
        """)
    
    st.divider()
    
    if st.session_state.uploaded_textbook_id:
        st.success(f"✅ Textbook loaded: **{st.session_state.uploaded_filename}**")
        st.info("👉 Now you can ask questions about the content!")
    else:
        st.info("👉 Start by uploading a textbook to begin learning!")


elif page == "Upload Content":
    st.header("📤 Upload Educational Content")
    
    st.write("Upload PDF files to use as learning material for tutoring and quizzes.")
    st.info("Supported formats: PDF only")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        st.write(f"**File selected:** {uploaded_file.name}")
        st.write(f"**File size:** {uploaded_file.size / 1024:.2f} KB")
        
        if st.button("Upload and Process", use_container_width=True):
            with st.spinner("Processing PDF... This may take a moment..."):
                try:
                    # Prepare file for upload
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    
                    # Upload to backend
                    response = requests.post(
                        f"{BACKEND_URL}/upload-textbook",
                        files=files,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Store upload info in session
                        st.session_state.uploaded_textbook_id = result["upload_id"]
                        st.session_state.uploaded_filename = result["filename"]
                        
                        st.success(f"✅ {result['message']}")
                        
                        # Display upload details
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Chunks Created", result["num_chunks"])
                        with col2:
                            st.metric("Total Characters", f"{result['total_characters']:,}")
                        with col3:
                            st.metric("Avg Chunk Size", f"{result['total_characters'] // result['num_chunks']:.0f}")
                        
                        st.divider()
                        
                        # Show preview
                        st.subheader("📋 Content Preview")
                        
                        preview_response = requests.get(
                            f"{BACKEND_URL}/textbooks/{result['upload_id']}/preview?chunk_count=3"
                        )
                        
                        if preview_response.status_code == 200:
                            preview_data = preview_response.json()
                            
                            for i, chunk in enumerate(preview_data["chunks"], 1):
                                with st.expander(f"Chunk {i} ({len(chunk)} chars)"):
                                    st.text(chunk[:500] + "..." if len(chunk) > 500 else chunk)
                    else:
                        error_detail = response.json().get("detail", "Unknown error")
                        st.error(f"❌ Upload failed: {error_detail}")
                
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend. Make sure the backend is running at " + BACKEND_URL)
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    else:
        st.warning("Please select a PDF file to upload")


elif page == "Ask Question":
    st.header("❓ Ask a Question")
    
    if not st.session_state.uploaded_textbook_id:
        st.warning("⚠️ Please upload a textbook first!")
        st.info("Go to **Upload Content** tab to upload a PDF")
    else:
        st.success(f"Using: **{st.session_state.uploaded_filename}**")
        
        col1, col2 = st.columns(2)
        with col1:
            student_name = st.text_input("Your Name")
        with col2:
            language = st.selectbox("Language", ["Nepali", "English"])
        
        question = st.text_area("Your Question", placeholder="Ask your question here...")
        
        if st.button("Get Answer", use_container_width=True):
            if question:
                with st.spinner("Generating answer..."):
                    try:
                        payload = {"question": question, "student_id": student_name or "anonymous"}
                        resp = requests.post(f"{BACKEND_URL}/ask", json=payload, timeout=30)
                        if resp.status_code == 200:
                            data = resp.json()
                            st.subheader("Answer (English)")
                            st.write(data.get("answer_english", "(no answer)"))

                            st.subheader("Explanation (Nepali)")
                            st.write(data.get("answer_nepali", "(no nepali explanation)"))

                            st.subheader("Quiz Questions")
                            qlist = data.get("quiz_questions", [])
                            if qlist:
                                for i, q in enumerate(qlist, 1):
                                    st.markdown(f"{i}. {q}")
                            else:
                                st.info("No quiz questions generated.")

                            st.subheader("Retrieved Sources")
                            sources = data.get("retrieved_sources", [])
                            if sources:
                                for s in sources:
                                    st.markdown(f"- {s.get('filename', '')} (score: {s.get('score')})")
                                    with st.expander("View excerpt"):
                                        st.text(s.get("content", ""))
                            else:
                                st.info("No textbook context found. Try uploading a textbook.")

                        else:
                            detail = resp.json().get("detail", resp.text)
                            st.error(f"Error from server: {detail}")
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to backend. Is it running?")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter a question first!")


elif page == "Take Quiz":
    st.header("🎯 Take a Quiz")
    
    if not st.session_state.uploaded_textbook_id:
        st.warning("⚠️ Please upload a textbook first!")
        st.info("Go to **Upload Content** tab to upload a PDF")
    else:
        st.success(f"Using: **{st.session_state.uploaded_filename}**")
        
        col1, col2 = st.columns(2)
        with col1:
            topic = st.text_input("Quiz Topic", placeholder="e.g., Chapter 1")
        with col2:
            num_questions = st.slider("Number of Questions", 5, 20, 10)
        
        language = st.radio("Language", ["Nepali", "English"], horizontal=True)

        if st.button("Generate Quiz", use_container_width=True):
            if topic:
                st.info("🔄 Generating quiz... (Feature coming soon - LLM integration needed)")
            else:
                st.warning("Please enter a topic first!")

        st.divider()
        st.subheader("Submit Quiz Result (Manual)")
        qcol1, qcol2 = st.columns(2)
        with qcol1:
            s_id = st.text_input("Student ID", value=student_name or "anonymous")
            s_name = st.text_input("Student Name", value=student_name or "")
            q_topic = st.text_input("Topic", value=topic or "")
        with qcol2:
            q_score = st.number_input("Score", min_value=0, value=0)
            q_total = st.number_input("Total Questions", min_value=1, value=5)
            q_lang = st.selectbox("Language", ["Nepali", "English"], index=1)

        if st.button("Submit Quiz Result", use_container_width=True):
            if not s_id:
                st.warning("Please enter Student ID")
            else:
                payload = {
                    "student_id": s_id,
                    "student_name": s_name,
                    "topic": q_topic,
                    "score": int(q_score),
                    "total": int(q_total),
                    "language": q_lang,
                }
                try:
                    resp = requests.post(f"{BACKEND_URL}/submit-quiz", json=payload, timeout=15)
                    if resp.status_code == 200:
                        st.success("✅ Quiz result submitted")
                        st.write(resp.json())
                    else:
                        st.error(f"Error: {resp.status_code} - {resp.text}")
                except Exception as e:
                    st.error(f"Failed to submit: {str(e)}")


elif page == "Parent Report":
    st.header("📊 Parent Progress Report")
    
    col1, col2 = st.columns(2)
    with col1:
        student_id = st.text_input("Student ID")
    with col2:
        period = st.selectbox("Report Period", ["Weekly", "Monthly"])

    language = st.radio("Report Language", ["Nepali", "English"], horizontal=True)

    if st.button("Generate Report", use_container_width=True):
        if student_id:
            try:
                resp = requests.get(f"{BACKEND_URL}/parent-summary/{student_id}", timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    st.subheader(f"Summary for {data.get('name') or data.get('student_id')}")
                    st.markdown("**Strengths:**")
                    strengths = data.get("strengths", [])
                    if strengths:
                        for s in strengths:
                            st.markdown(f"- {s}")
                    else:
                        st.markdown("- (none yet)")

                    st.markdown("**Weak Topics:**")
                    weak = data.get("weak_topics", [])
                    if weak:
                        for w in weak:
                            st.markdown(f"- {w}")
                    else:
                        st.markdown("- (none yet)")

                    st.markdown("**Suggested Next Practice:**")
                    sug = data.get("suggested_next_practice", [])
                    if sug:
                        for t in sug:
                            st.markdown(f"- {t}")
                    else:
                        st.markdown("- Practice recent topics")

                    st.markdown("**Note:**")
                    st.info(data.get("encouraging_note", "Keep practicing!"))

                else:
                    st.error(f"Error fetching summary: {resp.status_code} - {resp.text}")
            except Exception as e:
                st.error(f"Failed to fetch summary: {str(e)}")
        else:
            st.warning("Please enter Student ID first!")

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #999; font-size: 12px; padding: 20px;'>
    Pathshala AI - Making quality education accessible in rural Nepal
    </div>
    """, unsafe_allow_html=True)
