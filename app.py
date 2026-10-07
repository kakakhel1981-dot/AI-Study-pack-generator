import streamlit as st
import os
import json
import re

from google import genai
from google.genai import types

from pypdf import PdfReader
from docx import Document


# ============================================================
# AI STUDY PACK GENERATOR
# Developed by Shahzad Amin
# Streamlit + Gemini
# ============================================================

MODEL_NAME = "gemini-3.7-flash"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Study Pack Generator",
    page_icon="📚",
    layout="centered"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #f8f9fb;
    }

    .main .block-container {
        max-width: 850px;
        padding-top: 25px;
        padding-bottom: 50px;
    }

    /* Main title */

    .main-title {
        text-align: center;
        font-size: 32px;
        font-weight: 700;
        color: #5b5cf6;
        margin-bottom: 5px;
    }

    .sub-title {
        text-align: center;
        color: #777;
        font-size: 16px;
        margin-bottom: 25px;
    }

    /* Settings card */

    .settings-card {
        background: white;
        padding: 22px;
        border-radius: 16px;
        box-shadow: 0px 3px 15px rgba(0,0,0,0.06);
        margin-bottom: 20px;
    }

    /* Field labels */

    .field-label {
        display: inline-block;
        background-color: #e7e8ff;
        color: #5b5cf6;
        font-size: 16px;
        font-weight: 700;
        padding: 5px 9px;
        border-radius: 7px;
        margin-top: 10px;
        margin-bottom: 5px;
    }

    /* Section headings */

    .section-heading {
        font-size: 22px;
        font-weight: 700;
        color: #202124;
        margin-top: 25px;
        margin-bottom: 12px;
    }

    /* Output cards */

    .output-card {
        background: white;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
        border: 1px solid #eeeeee;
        box-shadow: 0px 2px 10px rgba(0,0,0,0.04);
    }

    .output-title {
        color: #5b5cf6;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .question {
        font-size: 16px;
        font-weight: 600;
        color: #222;
    }

    .answer {
        margin-top: 8px;
        color: #333;
    }

    .answer-label {
        color: #5b5cf6;
        font-weight: 700;
    }

    .credit {
        text-align: center;
        color: #888;
        margin-top: 35px;
        font-size: 14px;
    }

    /* Buttons */

    .stButton > button {
        border-radius: 10px;
        min-height: 45px;
        font-weight: 700;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# API KEY
# ============================================================

def get_api_key():

    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""

    if not key:
        key = os.getenv("GEMINI_API_KEY", "")

    return key


# ============================================================
# FILE READER
# ============================================================

def read_uploaded_file(uploaded_file):

    if uploaded_file is None:
        return ""

    filename = uploaded_file.name.lower()

    try:

        # TXT
        if filename.endswith(".txt"):
            return uploaded_file.getvalue().decode(
                "utf-8",
                errors="ignore"
            )

        # PDF
        elif filename.endswith(".pdf"):

            reader = PdfReader(uploaded_file)

            text = ""

            for page in reader.pages:
                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"

            return text

        # DOCX
        elif filename.endswith(".docx"):

            document = Document(uploaded_file)

            text = ""

            for paragraph in document.paragraphs:
                text += paragraph.text + "\n"

            return text

    except Exception as e:

        st.error(
            f"Could not read the uploaded file: {e}"
        )

    return ""


# ============================================================
# JSON CLEANER
# ============================================================

def clean_json(response_text):

    text = response_text.strip()

    # Remove ```json
    text = re.sub(
        r"^```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove ```
    text = re.sub(
        r"```$",
        "",
        text
    )

    text = text.strip()

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:

        text = text[start:end + 1]

    return text


# ============================================================
# PROMPT
# ============================================================

def create_prompt(
    subject,
    topic,
    grade,
    language,
    difficulty,
    mcq_count,
    short_count,
    long_count,
    flashcard_count,
    study_material
):

    material = study_material[:30000]

    prompt = f"""

You are an expert teacher and examination preparation assistant.

Create a complete study pack.

SUBJECT:
{subject}

TOPIC:
{topic}

GRADE / LEVEL:
{grade}

LANGUAGE:
{language}

DIFFICULTY:
{difficulty}

NUMBER OF MCQs:
{mcq_count}

NUMBER OF SHORT QUESTIONS:
{short_count}

NUMBER OF LONG QUESTIONS:
{long_count}

NUMBER OF FLASHCARDS:
{flashcard_count}


OPTIONAL STUDY MATERIAL:

{material if material else "No study material was uploaded."}


IMPORTANT INSTRUCTIONS:

1. Create accurate educational content.
2. Keep the difficulty appropriate for the selected level.
3. Use clear exam-friendly language.
4. If Urdu is selected, write the answers in Urdu.
5. If Simple English is selected, use simple English.
6. MCQs must have four options.
7. Provide correct answers and explanations.
8. Provide useful model answers.
9. Create exactly 7 days in the study plan.
10. Return ONLY valid JSON.
11. Do not add Markdown outside the JSON.


RETURN THIS EXACT JSON STRUCTURE:

{{
    "summary": "Topic summary",

    "key_concepts": [
        "Concept 1",
        "Concept 2",
        "Concept 3"
    ],

    "important_terms": [
        {{
            "term": "Term",
            "meaning": "Meaning"
        }}
    ],

    "mcqs": [
        {{
            "question": "Question",
            "options": [
                "A",
                "B",
                "C",
                "D"
            ],
            "answer": "Correct option",
            "explanation": "Explanation"
        }}
    ],

    "short_questions": [
        {{
            "question": "Question",
            "answer": "Model answer"
        }}
    ],

    "long_questions": [
        {{
            "question": "Exam question",
            "answer": "Detailed model answer"
        }}
    ],

    "flashcards": [
        {{
            "front": "Question or term",
            "back": "Answer or definition"
        }}
    ],

    "study_plan": [
        {{
            "day": "Day 1",
            "topics": "Topics",
            "activities": "Activities",
            "revision": "Revision"
        }},
        {{
            "day": "Day 2",
            "topics": "Topics",
            "activities": "Activities",
            "revision": "Revision"
        }},
        {{
            "day": "Day 3",
            "topics": "Topics",
            "activities": "Activities",
            "revision": "Revision"
        }},
        {{
            "day": "Day 4",
            "topics": "Topics",
            "activities": "Activities",
            "revision": "Revision"
        }},
        {{
            "day": "Day 5",
            "topics": "Topics",
            "activities": "Activities",
            "revision": "Revision"
        }},
        {{
            "day": "Day 6",
            "topics": "Topics",
            "activities": "Activities",
            "revision": "Revision"
        }},
        {{
            "day": "Day 7",
            "topics": "Topics",
            "activities": "Activities",
            "revision": "Revision"
        }}
    ],

    "exam_tips": [
        "Tip 1",
        "Tip 2",
        "Tip 3"
    ],

    "revision_checklist": [
        "Revision item 1",
        "Revision item 2",
        "Revision item 3"
    ]
}}

"""

    return prompt


# ============================================================
# GENERATE CONTENT
# ============================================================

def generate_study_pack(prompt):

    api_key = get_api_key()

    if not api_key:

        raise ValueError(
            "GEMINI_API_KEY is missing. "
            "Please add it in Streamlit Secrets."
        )

    client = genai.Client(
        api_key=api_key
    )

    response = client.models.generate_content(

        model=MODEL_NAME,

        contents=prompt,

        config=types.GenerateContentConfig(

            temperature=0.4,

            max_output_tokens=14000,

            response_mime_type="application/json"
        )
    )

    json_text = clean_json(response.text)

    return json.loads(json_text)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">📚 AI Study Pack Generator</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    'Create summaries, MCQs, questions, flashcards and a 7-day study plan'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# INPUT CARD
# ============================================================

st.markdown(
    '<div class="settings-card">',
    unsafe_allow_html=True
)


# SUBJECT

st.markdown(
    '<div class="field-label">Subject</div>',
    unsafe_allow_html=True
)

subject = st.text_input(
    "Subject",
    value="Computer",
    label_visibility="collapsed"
)


# TOPIC

st.markdown(
    '<div class="field-label">Topic</div>',
    unsafe_allow_html=True
)

topic = st.text_input(
    "Topic",
    value="Artificial Intelligence",
    label_visibility="collapsed"
)


# GRADE

st.markdown(
    '<div class="field-label">Grade / Level</div>',
    unsafe_allow_html=True
)

grade = st.selectbox(
    "Grade / Level",
    [
        "School - Beginner",
        "School - Intermediate",
        "School - Advanced",
        "College / University",
        "Professional"
    ],
    index=1,
    label_visibility="collapsed"
)


# LANGUAGE

st.markdown(
    '<div class="field-label">Language</div>',
    unsafe_allow_html=True
)

language = st.selectbox(
    "Language",
    [
        "English",
        "Urdu",
        "Simple English"
    ],
    label_visibility="collapsed"
)


# DIFFICULTY

st.markdown(
    '<div class="field-label">Difficulty</div>',
    unsafe_allow_html=True
)

difficulty = st.selectbox(
    "Difficulty",
    [
        "Easy",
        "Medium",
        "Hard"
    ],
    index=1,
    label_visibility="collapsed"
)


# MCQ COUNT

st.markdown(
    '<div class="field-label">Number of MCQs</div>',
    unsafe_allow_html=True
)

mcq_count = st.slider(
    "Number of MCQs",
    min_value=3,
    max_value=30,
    value=10,
    label_visibility="collapsed"
)


st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# INCLUDE IN STUDY PACK
# ============================================================

st.markdown(
    '<div class="section-heading">Include in Study Pack</div>',
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

with col1:

    include_summary = st.checkbox(
        "📖 Topic Summary",
        value=True
    )

    include_mcqs = st.checkbox(
        "❓ MCQs with Answers",
        value=True
    )

    include_short = st.checkbox(
        "✍️ Short-Answer Questions",
        value=True
    )

    include_long = st.checkbox(
        "📝 Long / Exam Questions",
        value=True
    )


with col2:

    include_flashcards = st.checkbox(
        "🧠 Flashcards",
        value=True
    )

    include_plan = st.checkbox(
        "📅 7-Day Study Plan",
        value=True
    )

    include_tips = st.checkbox(
        "🎯 Exam Tips",
        value=True
    )

    include_checklist = st.checkbox(
        "✅ Revision Checklist",
        value=True
    )


# ============================================================
# ADVANCED OPTIONS
# ============================================================

with st.expander("⚙️ Advanced Options"):

    short_count = st.slider(
        "Number of Short Questions",
        3,
        15,
        5
    )

    long_count = st.slider(
        "Number of Long Questions",
        2,
        10,
        3
    )

    flashcard_count = st.slider(
        "Number of Flashcards",
        5,
        30,
        10
    )


# ============================================================
# FILE UPLOAD
# ============================================================

st.markdown(
    '<div class="section-heading">📄 Optional Study Material</div>',
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader(
    "Upload TXT, PDF or DOCX",
    type=[
        "txt",
        "pdf",
        "docx"
    ]
)


# ============================================================
# GENERATE BUTTON
# ============================================================

generate_button = st.button(
    "✨ Generate Study Pack",
    type="primary",
    use_container_width=True
)


# ============================================================
# GENERATE
# ============================================================

if generate_button:

    if not subject.strip():

        st.warning(
            "Please enter a subject."
        )

        st.stop()


    if not topic.strip():

        st.warning(
            "Please enter a topic."
        )

        st.stop()


    study_material = ""

    if uploaded_file:

        study_material = read_uploaded_file(
            uploaded_file
        )


    prompt = create_prompt(

        subject=subject,

        topic=topic,

        grade=grade,

        language=language,

        difficulty=difficulty,

        mcq_count=mcq_count,

        short_count=short_count,

        long_count=long_count,

        flashcard_count=flashcard_count,

        study_material=study_material
    )


    with st.spinner(
        "Creating your study pack..."
    ):

        try:

            result = generate_study_pack(
                prompt
            )

            st.session_state.study_pack = result

            st.success(
                "Study pack generated successfully!"
            )

        except Exception as e:

            st.error(
                f"Error generating study pack: {e}"
            )


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "study_pack" in st.session_state:

    data = st.session_state.study_pack


    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if include_summary:

        st.markdown(
            '<div class="section-heading">📖 Topic Summary</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="output-card">

                <div class="output-title">
                    Topic Summary
                </div>

                <div>
                    {data.get("summary", "")}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    # --------------------------------------------------------
    # KEY CONCEPTS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-heading">🔑 Key Concepts</div>',
        unsafe_allow_html=True
    )

    concepts = data.get(
        "key_concepts",
        []
    )

    for i, concept in enumerate(
        concepts,
        start=1
    ):

        st.markdown(
            f"""
            <div class="output-card">

                <div class="output-title">
                    Concept {i}
                </div>

                {concept}

            </div>
            """,
            unsafe_allow_html=True
        )


    # --------------------------------------------------------
    # IMPORTANT TERMS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-heading">📚 Important Terms</div>',
        unsafe_allow_html=True
    )

    for item in data.get(
        "important_terms",
        []
    ):

        st.markdown(
            f"""
            <div class="output-card">

                <div class="output-title">
                    {item.get("term", "")}
                </div>

                <div>
                    {item.get("meaning", "")}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    # --------------------------------------------------------
    # MCQs
    # --------------------------------------------------------

    if include_mcqs:

        st.markdown(
            '<div class="section-heading">❓ MCQs</div>',
            unsafe_allow_html=True
        )

        for i, mcq in enumerate(
            data.get("mcqs", []),
            start=1
        ):

            options_html = ""

            for option in mcq.get(
                "options",
                []
            ):

                options_html += (
                    f"<div>• {option}</div>"
                )


            st.markdown(
                f"""
                <div class="output-card">

                    <div class="output-title">
                        MCQ {i}
                    </div>

                    <div class="question">
                        {mcq.get("question", "")}
                    </div>

                    <br>

                    {options_html}

                    <div class="answer">
                        <span class="answer-label">
                            Correct Answer:
                        </span>
                        {mcq.get("answer", "")}
                    </div>

                    <div class="answer">
                        <span class="answer-label">
                            Explanation:
                        </span>
                        {mcq.get("explanation", "")}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )


    # --------------------------------------------------------
    # SHORT QUESTIONS
    # --------------------------------------------------------

    if include_short:

        st.markdown(
            '<div class="section-heading">✍️ Short-Answer Questions</div>',
            unsafe_allow_html=True
        )

        for i, item in enumerate(
            data.get(
                "short_questions",
                []
            ),
            start=1
        ):

            st.markdown(
                f"""
                <div class="output-card">

                    <div class="output-title">
                        Question {i}
                    </div>

                    <div class="question">
                        {item.get("question", "")}
                    </div>

                    <div class="answer">

                        <span class="answer-label">
                            Model Answer:
                        </span>

                        {item.get("answer", "")}

                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )


    # --------------------------------------------------------
    # LONG QUESTIONS
    # --------------------------------------------------------

    if include_long:

        st.markdown(
            '<div class="section-heading">📝 Long / Exam Questions</div>',
            unsafe_allow_html=True
        )

        for i, item in enumerate(
            data.get(
                "long_questions",
                []
            ),
            start=1
        ):

            st.markdown(
                f"""
                <div class="output-card">

                    <div class="output-title">
                        Exam Question {i}
                    </div>

                    <div class="question">
                        {item.get("question", "")}
                    </div>

                    <div class="answer">

                        <span class="answer-label">
                            Model Answer:
                        </span>

                        {item.get("answer", "")}

                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )


    # --------------------------------------------------------
    # FLASHCARDS
    # --------------------------------------------------------

    if include_flashcards:

        st.markdown(
            '<div class="section-heading">🧠 Flashcards</div>',
            unsafe_allow_html=True
        )

        for i, card in enumerate(
            data.get(
                "flashcards",
                []
            ),
            start=1
        ):

            st.markdown(
                f"""
                <div class="output-card">

                    <div class="output-title">
                        Flashcard {i}
                    </div>

                    <div>
                        <b>Front:</b>
                        {card.get("front", "")}
                    </div>

                    <br>

                    <div>
                        <span class="answer-label">
                            Back:
                        </span>

                        {card.get("back", "")}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )


    # --------------------------------------------------------
    # 7 DAY STUDY PLAN
    # --------------------------------------------------------

    if include_plan:

        st.markdown(
            '<div class="section-heading">📅 7-Day Study Plan</div>',
            unsafe_allow_html=True
        )

        for day in data.get(
            "study_plan",
            []
        ):

            st.markdown(
                f"""
                <div class="output-card">

                    <div class="output-title">
                        {day.get("day", "")}
                    </div>

                    <b>Topics:</b>
                    {day.get("topics", "")}

                    <br><br>

                    <b>Activities:</b>
                    {day.get("activities", "")}

                    <br><br>

                    <b>Revision:</b>
                    {day.get("revision", "")}

                </div>
                """,
                unsafe_allow_html=True
            )


    # --------------------------------------------------------
    # EXAM TIPS
    # --------------------------------------------------------

    if include_tips:

        st.markdown(
            '<div class="section-heading">🎯 Exam Tips</div>',
            unsafe_allow_html=True
        )

        for tip in data.get(
            "exam_tips",
            []
        ):

            st.markdown(
                f"""
                <div class="output-card">
                    ✅ {tip}
                </div>
                """,
                unsafe_allow_html=True
            )


    # --------------------------------------------------------
    # REVISION CHECKLIST
    # --------------------------------------------------------

    if include_checklist:

        st.markdown(
            '<div class="section-heading">✅ Revision Checklist</div>',
            unsafe_allow_html=True
        )

        for item in data.get(
            "revision_checklist",
            []
        ):

            st.markdown(
                f"""
                <div class="output-card">
                    ☐ {item}
                </div>
                """,
                unsafe_allow_html=True
            )


    # ========================================================
    # DOWNLOAD MARKDOWN
    # ========================================================

    markdown_text = f"""# AI Study Pack

## Subject
{subject}

## Topic
{topic}

## Grade / Level
{grade}

## Language
{language}

## Difficulty
{difficulty}


# Topic Summary

{data.get("summary", "")}


# Key Concepts

"""

    for concept in data.get(
        "key_concepts",
        []
    ):

        markdown_text += (
            f"- {concept}\n"
        )


    markdown_text += "\n# MCQs\n\n"


    for i, mcq in enumerate(
        data.get("mcqs", []),
        start=1
    ):

        markdown_text += (
            f"## MCQ {i}\n"
            f"{mcq.get('question', '')}\n\n"
        )

        for option in mcq.get(
            "options",
            []
        ):

            markdown_text += (
                f"- {option}\n"
            )

        markdown_text += (
            f"\n**Answer:** "
            f"{mcq.get('answer', '')}\n\n"
        )

        markdown_text += (
            f"**Explanation:** "
            f"{mcq.get('explanation', '')}\n\n"
        )


    markdown_text += (
        "\n# Short Questions\n\n"
    )


    for i, item in enumerate(
        data.get(
            "short_questions",
            []
        ),
        start=1
    ):

        markdown_text += (
            f"## Question {i}\n"
            f"{item.get('question', '')}\n\n"
            f"**Answer:** "
            f"{item.get('answer', '')}\n\n"
        )


    markdown_text += (
        "\n# Long / Exam Questions\n\n"
    )


    for i, item in enumerate(
        data.get(
            "long_questions",
            []
        ),
        start=1
    ):

        markdown_text += (
            f"## Exam Question {i}\n"
            f"{item.get('question', '')}\n\n"
            f"**Model Answer:** "
            f"{item.get('answer', '')}\n\n"
        )


    markdown_text += (
        "\n# Flashcards\n\n"
    )


    for i, card in enumerate(
        data.get(
            "flashcards",
            []
        ),
        start=1
    ):

        markdown_text += (
            f"## Flashcard {i}\n"
            f"**Front:** {card.get('front', '')}\n\n"
            f"**Back:** {card.get('back', '')}\n\n"
        )


    markdown_text += (
        "\n# 7-Day Study Plan\n\n"
    )


    for day in data.get(
        "study_plan",
        []
    ):

        markdown_text += (
            f"## {day.get('day', '')}\n"
            f"**Topics:** {day.get('topics', '')}\n\n"
            f"**Activities:** {day.get('activities', '')}\n\n"
            f"**Revision:** {day.get('revision', '')}\n\n"
        )


    markdown_text += (
        "\n# Exam Tips\n\n"
    )


    for tip in data.get(
        "exam_tips",
        []
    ):

        markdown_text += (
            f"- {tip}\n"
        )


    markdown_text += (
        "\n\n# Revision Checklist\n\n"
    )


    for item in data.get(
        "revision_checklist",
        []
    ):

        markdown_text += (
            f"- [ ] {item}\n"
        )


    markdown_text += (
        "\n\n---\n"
        "Developed by Shahzad Amin"
    )


    st.download_button(

        label="⬇️ Download Study Pack",

        data=markdown_text,

        file_name="AI_Study_Pack.md",

        mime="text/markdown",

        use_container_width=True
    )


# ============================================================
# CREDIT
# ============================================================

st.markdown(
    '<div class="credit">Developed by Shahzad Amin</div>',
    unsafe_allow_html=True
)
