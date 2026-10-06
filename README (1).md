# 🕵️ Intelligent Code Reviewer & Explainer

A developer utility that analyzes a raw code file, identifies bugs, and explains the code in plain language — built with Streamlit.

## What it does

- Ingests a raw code file (`.py`, `.js`, `.java`, `.ts`, ...) as a string, via upload or paste.
- Sends it to an LLM under a strict **system prompt** that forces a structured JSON response.
- Renders three distinct sections:
  1. **Plain-language explanation** of what the code does
  2. **Bug report** — issues found, with severity and detail
  3. **Optimized code** — a corrected version, syntax-highlighted

## Providers

- **Google (Gemini)** — default. Uses the modern `google-genai` SDK and Google AI Studio's free tier.
- **OpenAI** — alternative, requires billing set up on your OpenAI account.
- **Anthropic (Claude)** — alternative, requires billing set up on your Anthropic account.

Switch between them anytime via the sidebar dropdown — no code changes needed.

## Setup

1. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   ```

2. Get a free API key from Google AI Studio: https://aistudio.google.com/apikey

3. Copy `.env.example` to `.env` and add your key:
   ```
   GOOGLE_API_KEY=AIza...
   ```
   You only need a key for the provider(s) you plan to use.

4. Run the app:
   ```
   streamlit run app.py
   ```

## How it works

- `reviewer.py` holds the system prompt and the calls to each provider's API. The system prompt forces the model to return **only** a JSON object with fixed keys (`language`, `explanation`, `bugs`, `optimized_code`), so the output is reliably structured rather than freeform text.
- `app.py` is the Streamlit UI: it ingests the code, calls `review_code()`, and renders each part of the structured response separately, using `st.code(...)` for syntax-highlighted output.

## Notes

- Never commit a real `.env` file; only `.env.example` should be tracked in git.
