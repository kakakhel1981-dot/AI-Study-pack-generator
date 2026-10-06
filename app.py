import os
import sys
from pathlib import Path

# ============================================================
# AI Study Pack Generator
# Gradio UI for Google Colab / local development
# Streamlit UI for Streamlit Cloud deployment
# ============================================================

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def get_api_key():
    """Read the Gemini API key from environment variables or Streamlit secrets."""
    key = os.getenv("GEMINI_API_KEY", "").strip()

    if not key:
        try:
            import streamlit as st
            key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
        except Exception:
            pass

    return key


def extract_uploaded_file(file_path):
    """Extract text from TXT, PDF, or DOCX files."""
    if not file_path:
        return ""

    path = Path(file_path)
    suffix = path.suffix.lower()

    try:
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            return "\n".join(pages)

        if suffix == ".docx":
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)

        return ""
    except Exception as exc:
        raise ValueError(f"Could not read the uploaded file: {exc}") from exc


def build_prompt(
    topic,
    grade_level,
    subject,
    language,
    difficulty,
    question_count,
    include_mcq,
    include_short,
    include_long,
    include_flashcards,
    include_summary,
    include_study_plan,
    source_text,
):
    sections = []

    if include_summary:
        sections.append("1. Topic Summary")
    if include_mcq:
        sections.append("2. Multiple Choice Questions (MCQs)")
    if include_short:
        sections.append("3. Short Answer Questions")
    if include_long:
        sections.append("4. Long Answer / Exam Questions")
    if include_flashcards:
        sections.append("5. Flashcards")
    if include_study_plan:
        sections.append("6. 7-Day Study Plan")

    if not sections:
        sections.append("1. Topic Summary")

    source_section = ""
    if source_text.strip():
        # Keep very large uploads manageable.
        source_text = source_text.strip()[:50000]
        source_section = f"""
SOURCE MATERIAL PROVIDED BY THE STUDENT
Use the following material as the primary reference. Do not invent facts
that conflict with it.

--- SOURCE START ---
{source_text}
--- SOURCE END ---
"""

    return f"""
You are an expert teacher, curriculum designer, and exam-preparation coach.

Create a high-quality AI Study Pack for the student.

STUDENT SETTINGS
- Subject: {subject}
- Topic: {topic}
- Grade / Level: {grade_level}
- Language: {language}
- Difficulty: {difficulty}
- Number of MCQs requested: {question_count}

REQUIRED SECTIONS
{chr(10).join(sections)}

QUALITY RULES
- Keep the content appropriate for the stated grade/level.
- Use clear, simple language unless the level requires technical language.
- Focus on understanding, revision, and exam preparation.
- Do not make up references, quotations, statistics, or facts.
- If source material is provided, prioritize it.
- Make questions meaningful rather than repetitive.
- Put the answer immediately after each MCQ as "Answer: X" and give a
  one-sentence explanation.
- For short and long questions, provide concise model answers.
- Flashcards should use a clear "Q:" and "A:" format.
- The study plan should be practical and achievable.
- Use Markdown headings and bullet points.
- Finish with a short "Exam Tips" section containing 5 practical tips.

CONTENT REQUIREMENTS
- Summary: key concepts, definitions, important points, and examples.
- MCQs: exactly {question_count} questions if MCQs are selected.
- Short questions: approximately 5 questions if selected.
- Long questions: approximately 3 questions if selected.
- Flashcards: approximately 10 cards if selected.
- Study plan: 7 daily sessions if selected.

Return ONLY the finished study pack in Markdown. Do not describe your process.
{source_section}
"""


def generate_study_pack(
    topic,
    grade_level,
    subject,
    language,
    difficulty,
    question_count,
    include_mcq,
    include_short,
    include_long,
    include_flashcards,
    include_summary,
    include_study_plan,
    uploaded_file=None,
):
    topic = (topic or "").strip()
    subject = (subject or "").strip()
    grade_level = (grade_level or "").strip()
    language = (language or "English").strip()
    difficulty = (difficulty or "Medium").strip()

    if not topic:
        return "Please enter a topic."
    if not subject:
        return "Please enter a subject."

    try:
        question_count = int(question_count)
    except (TypeError, ValueError):
        question_count = 10

    question_count = max(3, min(question_count, 30))

    source_text = ""
    if uploaded_file:
        source_text = extract_uploaded_file(uploaded_file)

    api_key = get_api_key()
    if not api_key:
        return (
            "### API Key Required\n\n"
            "Please set `GEMINI_API_KEY` before generating a study pack.\n\n"
            "**Google Colab:** run the API-key cell shown in the guide.\n\n"
            "**Streamlit Cloud:** add `GEMINI_API_KEY` under "
            "**App settings → Secrets**."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = build_prompt(
            topic=topic,
            grade_level=grade_level,
            subject=subject,
            language=language,
            difficulty=difficulty,
            question_count=question_count,
            include_mcq=include_mcq,
            include_short=include_short,
            include_long=include_long,
            include_flashcards=include_flashcards,
            include_summary=include_summary,
            include_study_plan=include_study_plan,
            source_text=source_text,
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=12000,
            ),
        )

        result = (response.text or "").strip()
        if not result:
            return "The AI returned an empty response. Please try again."

        return result

    except Exception as exc:
        return (
            "### Generation Error\n\n"
            f"`{type(exc).__name__}: {exc}`\n\n"
            "Please verify your API key, internet connection, and Gemini "
            "model availability, then try again."
        )


def save_markdown(study_pack):
    """Save generated content as a Markdown file."""
    output_path = Path("AI_Study_Pack.md")
    output_path.write_text(study_pack or "", encoding="utf-8")
    return str(output_path)


def build_gradio_app():
    import gradio as gr

    css = """
    .title { text-align: center; }
    .credit { text-align: center; font-size: 14px; }
    """

    with gr.Blocks(title="AI Study Pack Generator", css=css, theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "# 📚 AI Study Pack Generator",
            elem_classes=["title"],
        )
        gr.Markdown(
            "Create summaries, MCQs, short questions, long questions, "
            "flashcards and a study plan with Gemini AI.",
            elem_classes=["title"],
        )

        with gr.Row():
            with gr.Column(scale=1):
                subject = gr.Textbox(
                    label="Subject",
                    placeholder="e.g., Computer Science",
                )
                topic = gr.Textbox(
                    label="Topic",
                    placeholder="e.g., Artificial Intelligence",
                )
                grade_level = gr.Dropdown(
                    choices=[
                        "School - Beginner",
                        "School - Intermediate",
                        "School - Advanced",
                        "College / University",
                        "Professional",
                    ],
                    value="School - Intermediate",
                    label="Grade / Level",
                )
                language = gr.Dropdown(
                    choices=["English", "Urdu", "Simple English"],
                    value="English",
                    label="Language",
                )
                difficulty = gr.Dropdown(
                    choices=["Easy", "Medium", "Hard"],
                    value="Medium",
                    label="Difficulty",
                )
                question_count = gr.Slider(
                    minimum=3,
                    maximum=30,
                    value=10,
                    step=1,
                    label="Number of MCQs",
                )

                gr.Markdown("### Include in Study Pack")
                include_summary = gr.Checkbox(value=True, label="Topic Summary")
                include_mcq = gr.Checkbox(value=True, label="MCQs")
                include_short = gr.Checkbox(value=True, label="Short Questions")
                include_long = gr.Checkbox(value=True, label="Long Questions")
                include_flashcards = gr.Checkbox(value=True, label="Flashcards")
                include_study_plan = gr.Checkbox(value=True, label="7-Day Study Plan")

                uploaded_file = gr.File(
                    label="Optional Notes / Material (TXT, PDF, DOCX)",
                    type="filepath",
                )

                generate_btn = gr.Button(
                    "🚀 Generate Study Pack",
                    variant="primary",
                )

            with gr.Column(scale=2):
                output = gr.Markdown(
                    value="Your generated study pack will appear here."
                )
                download_btn = gr.DownloadButton(
                    "⬇️ Download Study Pack (.md)",
                    visible=False,
                )

        gr.Markdown(
            "Developed by **Shahzad Amin** | AI Study Pack Generator"
            "",
            elem_classes=["credit"],
        )

        def generate_and_prepare(*args):
            pack = generate_study_pack(*args)
            if pack.startswith("### API Key Required") or pack.startswith("### Generation Error"):
                return pack, gr.update(visible=False, value=None)

            path = save_markdown(pack)
            return pack, gr.update(visible=True, value=path)

        generate_btn.click(
            fn=generate_and_prepare,
            inputs=[
                topic,
                grade_level,
                subject,
                language,
                difficulty,
                question_count,
                include_mcq,
                include_short,
                include_long,
                include_flashcards,
                include_summary,
                include_study_plan,
                uploaded_file,
            ],
            outputs=[output, download_btn],
        )

    return demo


def run_gradio():
    demo = build_gradio_app()
    demo.launch(share=True)


def run_streamlit():
    import streamlit as st

    st.set_page_config(
        page_title="AI Study Pack Generator",
        page_icon="📚",
        layout="wide",
    )

    st.title("📚 AI Study Pack Generator")
    st.caption(
        "Create an AI-powered study pack using Gemini 3.8 Flash."
    )

    with st.sidebar:
        st.header("Study Settings")
        subject = st.text_input("Subject", "Computer Science")
        topic = st.text_input("Topic", "Artificial Intelligence")
        grade_level = st.selectbox(
            "Grade / Level",
            [
                "School - Beginner",
                "School - Intermediate",
                "School - Advanced",
                "College / University",
                "Professional",
            ],
        )
        language = st.selectbox(
            "Language", ["English", "Urdu", "Simple English"]
        )
        difficulty = st.selectbox(
            "Difficulty", ["Easy", "Medium", "Hard"], index=1
        )
        question_count = st.slider(
            "Number of MCQs", 3, 30, 10
        )

        st.subheader("Include")
        include_summary = st.checkbox("Topic Summary", True)
        include_mcq = st.checkbox("MCQs", True)
        include_short = st.checkbox("Short Questions", True)
        include_long = st.checkbox("Long Questions", True)
        include_flashcards = st.checkbox("Flashcards", True)
        include_study_plan = st.checkbox("7-Day Study Plan", True)

        uploaded = st.file_uploader(
            "Optional Notes / Material",
            type=["txt", "pdf", "docx"],
            help="Upload notes to make the study pack more specific.",
        )

        generate = st.button(
            "🚀 Generate Study Pack",
            type="primary",
            use_container_width=True,
        )

    if generate:
        temp_path = None

        if uploaded:
            suffix = Path(uploaded.name).suffix
            temp_path = Path("uploaded_source" + suffix)
            temp_path.write_bytes(uploaded.getvalue())

        with st.spinner("Generating your study pack..."):
            result = generate_study_pack(
                topic,
                grade_level,
                subject,
                language,
                difficulty,
                question_count,
                include_mcq,
                include_short,
                include_long,
                include_flashcards,
                include_summary,
                include_study_plan,
                str(temp_path) if temp_path else None,
            )

        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)

        st.markdown(result)

        if not result.startswith("### API Key Required") and not result.startswith("### Generation Error"):
            st.download_button(
                "⬇️ Download Study Pack (.md)",
                data=result,
                file_name="AI_Study_Pack.md",
                mime="text/markdown",
                use_container_width=True,
            )

    st.divider()
    st.caption("Developed by Shahzad Amin | AI Study Pack Generator")


# Streamlit Cloud runs the file through the Streamlit executable.
# Running `python app.py` starts Gradio, which is convenient in Colab.
if "streamlit" in os.path.basename(sys.argv[0]).lower():
    run_streamlit()
else:
    run_gradio()
