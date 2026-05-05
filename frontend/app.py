"""
Pathshala AI - Streamlit Frontend
Bilingual interface for students and parents
"""
import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Pathshala AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        "Ask Question",
        "Take Quiz",
        "Parent Report",
        "Upload Content"
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
    st.info("👉 Select an option from the menu to get started!")


elif page == "Ask Question":
    st.header("❓ Ask a Question")
    
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("Your Name")
    with col2:
        language = st.selectbox("Language", ["Nepali", "English"])
    
    question = st.text_area("Your Question", placeholder="Ask your question here...")
    
    if st.button("Get Answer", use_container_width=True):
        if question:
            st.info("Processing your question... (Feature coming soon)")
        else:
            st.warning("Please enter a question first!")


elif page == "Take Quiz":
    st.header("🎯 Take a Quiz")
    
    col1, col2 = st.columns(2)
    with col1:
        topic = st.selectbox("Select Topic", ["Math", "Science", "Language"])
    with col2:
        num_questions = st.slider("Number of Questions", 5, 20, 10)
    
    language = st.radio("Language", ["Nepali", "English"], horizontal=True)
    
    if st.button("Start Quiz", use_container_width=True):
        st.info("Quiz generator coming soon! (Feature in development)")


elif page == "Parent Report":
    st.header("📊 Parent Progress Report")
    
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("Student Name")
    with col2:
        period = st.selectbox("Report Period", ["Weekly", "Monthly"])
    
    language = st.radio("Report Language", ["Nepali", "English"], horizontal=True)
    
    if st.button("Generate Report", use_container_width=True):
        st.info("Report generation coming soon! (Feature in development)")


elif page == "Upload Content":
    st.header("📤 Upload Educational Content")
    
    st.write("Upload PDF files or educational materials to enhance the learning experience.")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        st.info(f"File '{uploaded_file.name}' received! (Processing coming soon)")
    
    if st.button("Upload", use_container_width=True, disabled=uploaded_file is None):
        st.success("Upload feature coming soon!")

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #999; font-size: 12px; padding: 20px;'>
    Pathshala AI - Making quality education accessible in rural Nepal
    </div>
    """, unsafe_allow_html=True)
