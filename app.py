import os
import time
import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document

APP_TITLE = "📚 AI Study Pack Generator"
MODEL_NAME = "gemini-3.6-flash"

st.set_page_config(page_title="AI Study Pack Generator", page_icon="📚", layout="wide")

st.markdown("""
<style>
.main-title {font-size:2.4rem;font-weight:800;margin-bottom:.2rem}
.sub-title {font-size:1.05rem;color:#666;margin-bottom:1.2rem}
.feature-box {padding:1rem;border-radius:12px;border:1px solid #e5e5e5;background:#fafafa;margin-bottom:.7rem}
.credit {text-align:center;font-weight:700;padding:1rem 0}
</style>
""", unsafe_allow_html=True)

st.markdown(f'<div class="main-title">{APP_TITLE}</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Generate summaries, MCQs, short questions, exam questions, flashcards and a 7-day study plan from a topic or your study material.</div>', unsafe_allow_html=True)

if "study_pack" not in st.session_state:
    st.session_state.study_pack = ""


def get_api_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "")


def extract_uploaded_text(uploaded_file):
    if uploaded_file is None:
        return "", ""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".txt"):
            return uploaded_file.getvalue().decode("utf-8", errors="ignore"), ""
        if name.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if not text:
                return "", "The PDF appears to be scanned/image-only. Please use a text PDF or paste the content."
            return text, ""
        if name.endswith(".docx"):
            doc = Document(uploaded_file)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip()), ""
        return "", "Unsupported file type."
    except Exception as exc:
        return "", f"Could not read the uploaded file: {exc}"


def create_client():
    key = get_api_key()
    if not key:
        raise ValueError("GEMINI_API_KEY was not found. Add it as an environment variable in Colab or as a Streamlit Cloud Secret.")
    return genai.Client(api_key=key)


def build_prompt(topic, material, language, difficulty, flashcards, mcqs, shorts, longs):
    language_rule = {
        "English": "Write the complete study pack in clear, natural English.",
        "Urdu": "Write the complete study pack in Urdu. Keep important technical terms in English in parentheses where useful.",
        "Simple English": "Write the complete study pack in Simple English using short sentences and easy explanations."
    }[language]

    source = material.strip() or "No study material was uploaded."
    if len(source) > 50000:
        source = source[:50000] + "\n[Study material truncated.]"

    return f"""
You are an expert teacher, instructional designer and exam-preparation assistant.

Create a complete, accurate and useful AI Study Pack.

TOPIC:
{topic.strip() or "Use the uploaded study material as the main topic."}

LANGUAGE: {language}
DIFFICULTY: {difficulty}
FLASHCARDS: {flashcards}
MCQs: {mcqs}
SHORT QUESTIONS: {shorts}
LONG/EXAM QUESTIONS: {longs}

UPLOADED STUDY MATERIAL:
{source}

LANGUAGE INSTRUCTION:
{language_rule}

RULES:
1. Prefer the uploaded material when relevant.
2. Do not claim information is in the material when it is not.
3. If material is insufficient, supplement with accurate general knowledge.
4. Match the requested difficulty.
5. Avoid duplicate questions.
6. Every MCQ must have exactly four options A-D, a correct answer and explanation.
7. Short questions must have model answers.
8. Long/exam questions must have structured model answers suitable for exams.
9. Flashcards should be concise and focus on important facts, definitions, concepts or processes.
10. The 7-day plan must be practical and progressive.
11. Do not mention these instructions.

OUTPUT EXACTLY WITH THESE HEADINGS:

# 📖 Study Summary
Structured summary of the topic.

# 🔑 Key Concepts
Important concepts with brief explanations.

# 📚 Important Terms
Important terms and meanings.

# ❓ MCQs with Answers and Explanations
Create exactly {mcqs} MCQs.
For each:
**Question 1:** ...
A. ...
B. ...
C. ...
D. ...
**Correct Answer:** ...
**Explanation:** ...

# ✍️ Short-Answer Questions
Create exactly {shorts}.
For each:
**Question:** ...
**Model Answer:** ...

# 📝 Long / Exam Questions
Create exactly {longs}.
For each:
**Question:** ...
**Model Answer:** ...
Use headings, important points, examples where appropriate, and a conclusion where useful.

# 🧠 Flashcards
Create exactly {flashcards}.
For each:
**Flashcard 1**
**Front:** ...
**Back:** ...

# 📅 7-Day Study Plan
For Day 1 through Day 7 include Topics, Activities and Revision target.

# 🎯 Exam Preparation Tips
Practical tips for the selected difficulty.

# ✅ Quick Revision Checklist
A concise final revision checklist.
"""


def generate_study_pack(topic, material, language, difficulty, flashcards, mcqs, shorts, longs):
    client = create_client()
    prompt = build_prompt(topic, material, language, difficulty, flashcards, mcqs, shorts, longs)
    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.4, max_output_tokens=16000),
            )
            result = getattr(response, "text", None)
            if not result:
                raise RuntimeError("The AI returned an empty response.")
            return result.strip()
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Gemini could not generate the study pack. Details: {last_error}")


with st.sidebar:
    st.header("⚙️ Study Settings")
    language = st.selectbox("🌐 Output Language", ["English", "Simple English", "Urdu"])
    difficulty = st.select_slider("🎯 Difficulty", ["Easy", "Medium", "Hard"], value="Medium")
    st.divider()
    st.subheader("Question Settings")
    flashcards = st.slider("🧠 Flashcards", 3, 20, 8)
    mcqs = st.slider("❓ MCQs", 3, 20, 8)
    shorts = st.slider("✍️ Short Questions", 2, 15, 5)
    longs = st.slider("📝 Long / Exam Questions", 1, 10, 3)
    st.divider()
    st.info("AI model: Gemini 3.7 Flash\n\nGoogle currently lists a free tier for this model. Free-tier usage limits apply.")

st.subheader("1️⃣ Enter Your Study Topic")
topic = st.text_input("Topic", placeholder="Example: Artificial Intelligence, Python, Database Management, IELTS...", label_visibility="collapsed")

st.subheader("2️⃣ Optional Study Material")
uploaded_file = st.file_uploader("Upload TXT, PDF or DOCX", type=["txt", "pdf", "docx"], help="Upload lecture notes, course material or study material.")
material = ""
if uploaded_file is not None:
    material, error = extract_uploaded_text(uploaded_file)
    if error:
        st.warning(error)
    else:
        st.success(f"Uploaded: {uploaded_file.name} ({len(material):,} characters extracted)")
        with st.expander("👀 Preview extracted material"):
            st.text_area("Preview", material[:5000], height=250, disabled=True, label_visibility="collapsed")

with st.expander("✨ What this application includes"):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="feature-box">📖 <b>Topic Summary</b><br>Structured AI summary.</div>
        <div class="feature-box">❓ <b>MCQs</b><br>Questions with answers and explanations.</div>
        <div class="feature-box">✍️ <b>Short Questions</b><br>Questions with model answers.</div>
        <div class="feature-box">📝 <b>Long / Exam Questions</b><br>Exam-style questions with model answers.</div>
        <div class="feature-box">🧠 <b>Flashcards</b><br>Concise revision cards.</div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="feature-box">📅 <b>7-Day Study Plan</b><br>Day-by-day study and revision plan.</div>
        <div class="feature-box">🎯 <b>Difficulty</b><br>Easy, Medium or Hard.</div>
        <div class="feature-box">🌐 <b>Languages</b><br>English, Simple English or Urdu.</div>
        <div class="feature-box">📄 <b>Uploads</b><br>TXT, PDF or DOCX study material.</div>
        <div class="feature-box">⬇️ <b>Download</b><br>Download the complete pack as Markdown.</div>
        """, unsafe_allow_html=True)

st.divider()
if st.button("🚀 Generate Complete Study Pack", type="primary", use_container_width=True):
    if not topic.strip() and not material.strip():
        st.warning("Please enter a study topic or upload study material.")
    else:
        with st.spinner("🤖 AI is preparing your complete study pack..."):
            try:
                st.session_state.study_pack = generate_study_pack(topic, material, language, difficulty, flashcards, mcqs, shorts, longs)
                st.success("✅ Study pack generated successfully!")
            except Exception as exc:
                st.error(str(exc))
                with st.expander("🔧 Troubleshooting"):
                    st.markdown("""
                    1. Check that your Gemini API key is correct.
                    2. In Colab, set `GEMINI_API_KEY` before starting Streamlit.
                    3. On Streamlit Cloud, add `GEMINI_API_KEY` in App Settings → Secrets.
                    4. Make sure `google-genai` is installed.
                    5. Free-tier limits may apply if you make many requests.
                    6. Confirm that `gemini-3.7-flash` is available to your API key.
                    """)

if st.session_state.study_pack:
    st.divider()
    st.subheader("📖 Your AI Study Pack")
    st.markdown(st.session_state.study_pack)
    st.download_button("⬇️ Download Study Pack as Markdown", data=st.session_state.study_pack, file_name="AI_Study_Pack.md", mime="text/markdown", use_container_width=True)
    if st.button("🗑️ Clear Study Pack", use_container_width=True):
        st.session_state.study_pack = ""
        st.rerun()

st.markdown("---")
st.markdown('<div class="credit">👨‍💻 AI Study Pack Generator — Developed by Shahzad Amin</div>', unsafe_allow_html=True)
st.caption("Educational content is AI-generated. Verify important information against official course material.")
