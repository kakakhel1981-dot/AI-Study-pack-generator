import os
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document

st.set_page_config(
    page_title="AI Study Pack Generator",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
<style>
.main-title {font-size: 2.3rem; font-weight: 700; margin-bottom: 0.2rem;}
.subtitle {font-size: 1.05rem; margin-bottom: 1.5rem;}
.card {padding: 1rem 1.2rem; border-radius: 12px; border: 1px solid #ddd; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📚 AI Study Pack Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Create a complete study pack with AI: summary, key concepts, flashcards, MCQs, short questions and a study plan.</div>',
    unsafe_allow_html=True
)

def get_api_key():
    # Streamlit Community Cloud: store GEMINI_API_KEY in App Settings > Secrets.
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "")

def extract_file_text(uploaded_file):
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()

    if name.endswith(".txt"):
        return uploaded_file.getvalue().decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)

    return ""

def generate_study_pack(topic, source_text, level, num_flashcards, num_mcqs, num_short):
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "Gemini API key not found. In Colab, set GEMINI_API_KEY before running the app. "
            "On Streamlit Cloud, add GEMINI_API_KEY in App Settings > Secrets."
        )

    client = genai.Client(api_key=api_key)

    source_section = source_text.strip()
    if len(source_section) > 30000:
        source_section = source_section[:30000] + "\n[Source text truncated for processing.]"

    prompt = f"""
You are an expert educational assistant.

Create a high-quality study pack for the learner.

Topic:
{topic if topic else "Use the uploaded study material as the topic."}

Education level:
{level}

Uploaded study material:
{source_section if source_section else "No file was uploaded. Use the topic provided above."}

Return the study pack in clear Markdown using EXACTLY these headings:

# Study Summary
Write a concise but useful explanation of the topic.

# Key Concepts
List the most important concepts with brief explanations.

# Important Terms
List important terms and their simple meanings.

# Flashcards
Create exactly {num_flashcards} flashcards.
Format each as:
**Q:** ...
**A:** ...

# Multiple Choice Questions
Create exactly {num_mcqs} MCQs.
For each question give four options (A-D), identify the correct answer, and give a one-sentence explanation.

# Short Questions
Create exactly {num_short} short-answer questions and provide a model answer for each.

# Study Tips
Give practical tips for remembering and understanding this topic.

# Quick Revision Checklist
Give a short checklist of the most important things the learner should revise.

Rules:
- Be accurate and educational.
- Use simple language appropriate for the selected education level.
- Do not invent facts from the uploaded material.
- If the uploaded material does not contain enough information, clearly supplement it with general knowledge.
- Make the output well structured and easy to study.
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )
    return response.text

with st.sidebar:
    st.header("⚙️ Study Pack Settings")

    level = st.selectbox(
        "Education Level",
        ["School", "College", "University", "Professional / Certification"]
    )

    num_flashcards = st.slider("Number of Flashcards", 3, 20, 8)
    num_mcqs = st.slider("Number of MCQs", 3, 20, 8)
    num_short = st.slider("Short Questions", 3, 15, 5)

    st.divider()
    st.info("Supported files: TXT, PDF and DOCX")

topic = st.text_input(
    "📌 Enter Study Topic",
    placeholder="Example: Artificial Intelligence, Database Management, Python, Networking..."
)

uploaded_file = st.file_uploader(
    "📄 Optional: Upload Study Material",
    type=["txt", "pdf", "docx"]
)

if uploaded_file:
    st.success(f"Uploaded: {uploaded_file.name}")

if st.button("🚀 Generate Study Pack", type="primary", use_container_width=True):
    if not topic.strip() and uploaded_file is None:
        st.warning("Please enter a topic or upload study material.")
    else:
        with st.spinner("Creating your study pack with AI..."):
            try:
                file_text = extract_file_text(uploaded_file)
                result = generate_study_pack(
                    topic.strip(),
                    file_text,
                    level,
                    num_flashcards,
                    num_mcqs,
                    num_short
                )

                st.session_state["study_pack"] = result
                st.success("Study pack generated successfully!")

            except Exception as e:
                st.error(f"Error: {e}")

if "study_pack" in st.session_state:
    st.divider()
    st.subheader("📖 Your AI Study Pack")
    st.markdown(st.session_state["study_pack"])

    st.download_button(
        "⬇️ Download Study Pack",
        data=st.session_state["study_pack"],
        file_name="AI_Study_Pack.md",
        mime="text/markdown",
        use_container_width=True
    )

st.divider()
st.caption("AI Study Pack Generator • Developed by Shahzad Amin")
