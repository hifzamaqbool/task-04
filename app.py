"""
app.py
------
Intelligent Code Reviewer & Explainer — a Streamlit developer utility that
ingests a raw code file (.py, .js, .java, ...) as a string, sends it to an
LLM under strict system formatting instructions, and renders back:

  1. A plain-language explanation of what the code does
  2. A distinct bug report (issues, severity, detail)
  3. An optimized / corrected code block

Uses Google's Gemini API by default (free tier via Google AI Studio),
with OpenAI and Anthropic available as alternatives.

Run with:
    streamlit run app.py
"""

import streamlit as st
from dotenv import load_dotenv

from reviewer import review_code, ReviewError

load_dotenv()  # pulls GOOGLE_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY from a local .env file, if present

st.set_page_config(
    page_title="Intelligent Code Reviewer & Explainer",
    page_icon="🕵️",
    layout="wide",
)

LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
}

SEVERITY_ICON = {
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
}

# ---------------------------------------------------------------------------
# Sidebar: provider / model settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    provider = st.selectbox("Model provider", ["google", "openai", "anthropic"], index=0)
    if provider == "google":
        model = st.text_input("Model", value="gemini-2.0-flash-001")
    elif provider == "openai":
        model = st.text_input("Model", value="gpt-4o-mini")
    else:
        model = st.text_input("Model", value="claude-3-5-sonnet-latest")
    st.caption("API keys are read from your local .env file and sent only to the provider you choose.")

st.title("🕵️ Intelligent Code Reviewer & Explainer")
st.caption("Paste or upload a code file. Get a bug report, a plain-language explanation, and an optimized version — in one pass.")

# ---------------------------------------------------------------------------
# Code ingestion: file upload or raw string paste
# ---------------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload a code file (.py, .js, .java, .ts, ...)",
    type=["py", "js", "jsx", "ts", "tsx", "java"],
)

default_code = ""
filename_hint = "snippet.py"
detected_ext = ".py"

if uploaded_file is not None:
    # Ingest the raw code file as a string, as required
    default_code = uploaded_file.read().decode("utf-8", errors="replace")
    filename_hint = uploaded_file.name
    for ext in LANG_MAP:
        if filename_hint.endswith(ext):
            detected_ext = ext
            break

code_input = st.text_area(
    "...or paste your code here",
    value=default_code,
    height=320,
    placeholder="def add(a, b):\n    return a - b  # bug: should be a + b",
)

analyze_clicked = st.button("🔍 Analyze code", type="primary")

# ---------------------------------------------------------------------------
# Run the analysis pipeline and render the structured result
# ---------------------------------------------------------------------------
if analyze_clicked:
    if not code_input.strip():
        st.warning("Please paste some code or upload a file first.")
    else:
        with st.spinner("Analyzing your code..."):
            try:
                result = review_code(
                    code=code_input,
                    filename_hint=filename_hint,
                    provider=provider,
                    model=model,
                )
            except ReviewError as e:
                st.error(str(e))
                result = None
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                result = None

        if result:
            lang = result.get("language", "unknown")
            display_lang = LANG_MAP.get(detected_ext, lang if lang != "unknown" else "python")

            st.divider()

            # --- Explanation ---
            st.subheader("📖 Plain-Language Explanation")
            st.markdown(result.get("explanation", "_No explanation returned._"))

            st.divider()

            # --- Bug report (kept visually distinct from the code) ---
            st.subheader("🐞 Bug Report")
            bugs = result.get("bugs", [])
            if not bugs:
                st.success("No bugs found — the code looks correct as-is.")
            else:
                for i, bug in enumerate(bugs, start=1):
                    severity = str(bug.get("severity", "low")).lower()
                    icon = SEVERITY_ICON.get(severity, "⚪")
                    title = bug.get("issue", "Untitled issue")
                    with st.expander(f"{icon} Bug {i}: {title} ({severity})", expanded=(severity == "high")):
                        st.markdown(bug.get("detail", ""))

            st.divider()

            # --- Optimized code, rendered with syntax highlighting ---
            st.subheader("✨ Optimized Code")
            st.code(result.get("optimized_code", code_input), language=display_lang, line_numbers=True)

            st.download_button(
                "⬇️ Download optimized code",
                data=result.get("optimized_code", code_input),
                file_name=f"optimized_{filename_hint}",
            )

st.divider()
with st.expander("ℹ️ How this works"):
    st.markdown(
        """
        1. Your code is sent to the selected LLM provider along with a strict **system prompt**
           that forces it to return a structured JSON object (`language`, `explanation`, `bugs`, `optimized_code`).
        2. The app parses that JSON and renders each part **separately** — so the bug report,
           the explanation, and the optimized code never get mixed together in one blob of text.
        3. Code is rendered with `st.code(...)`, which gives you proper syntax highlighting
           for the detected language.
        """
    )