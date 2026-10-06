"""
reviewer.py
-----------
Handles calling the LLM providers (Google Gemini, OpenAI, or Anthropic) to
analyze a code block and return a structured review: bug report,
plain-language explanation, and an optimized/fixed version of the code.

This is the "code analysis pipeline" — it owns the system prompt that forces
a structured JSON response, and the parsing logic that turns raw model text
into a reliable Python dict.

Google's Gemini API (via Google AI Studio) is the default provider.
"""

import os
import json
import re

# ---------------------------------------------------------------------------
# System formatting instructions
# ---------------------------------------------------------------------------
# This is the core of the "structured outputs" requirement: the model is
# forced to return ONLY a JSON object with a fixed schema, so the UI layer
# never has to guess where the bug report ends and the code begins.
SYSTEM_PROMPT = """You are an expert senior software engineer acting as an automated code reviewer.

You will be given a raw source code file. You must:
1. Carefully analyze it for bugs, logic errors, security issues, and bad practices.
2. Explain what the code does in plain, beginner-friendly language.
3. Produce an optimized / corrected version of the code that fixes the bugs you found.

You MUST respond with ONLY a single valid JSON object (no markdown fences, no extra commentary) with exactly these keys:

{
  "language": "detected programming language",
  "explanation": "plain language explanation of what the code does, as a single markdown string",
  "bugs": [
    {"issue": "short title of the bug", "detail": "explanation of the bug and why it's a problem", "severity": "low|medium|high"}
  ],
  "optimized_code": "the corrected/optimized full code as a single string, with no markdown fences inside it"
}

If you find no bugs, return an empty list for "bugs" but still provide the explanation and an optimized_code
(it can be identical to the input if no improvement is possible). Do not include any text outside the JSON object.
"""


class ReviewError(Exception):
    """Raised for any expected failure (missing key, bad response, empty input)."""
    pass


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from the model's raw text output.

    Models sometimes wrap JSON in markdown fences or add stray text despite
    instructions not to — this makes parsing robust to that.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = text[start:end + 1]
            return json.loads(snippet)
        raise ReviewError("Could not parse a JSON response from the model.")


def _call_google(code: str, filename_hint: str, model: str) -> str:
    """Call Google's Gemini API using the modern unified google-genai SDK."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ReviewError("GOOGLE_API_KEY is not set in your environment (.env).")

    client = genai.Client(api_key=api_key)
    user_prompt = f"Filename hint: {filename_hint}\n\nCode to review:\n{code}"

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
    )
    return response.text


def _call_openai(code: str, filename_hint: str, model: str) -> str:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ReviewError("OPENAI_API_KEY is not set in your environment (.env).")

    client = OpenAI(api_key=api_key)
    user_prompt = f"Filename hint: {filename_hint}\n\nCode to review:\n{code}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def _call_anthropic(code: str, filename_hint: str, model: str) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ReviewError("ANTHROPIC_API_KEY is not set in your environment (.env).")

    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = f"Filename hint: {filename_hint}\n\nCode to review:\n{code}"

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def review_code(code: str, filename_hint: str = "snippet.py", provider: str = "google",
                 model: str = None) -> dict:
    """
    Analyze a block of code and return a dict with keys:
    language, explanation, bugs (list of dicts), optimized_code.

    Raises ReviewError on missing API keys, empty input, or unparseable output.
    Defaults to Google's Gemini API (free tier via Google AI Studio).
    """
    if not code or not code.strip():
        raise ReviewError("No code was provided to review.")

    if provider == "google":
        model = model or "gemini-2.0-flash-001"
        raw = _call_google(code, filename_hint, model)
    elif provider == "openai":
        model = model or "gpt-4o-mini"
        raw = _call_openai(code, filename_hint, model)
    elif provider == "anthropic":
        model = model or "claude-3-5-sonnet-latest"
        raw = _call_anthropic(code, filename_hint, model)
    else:
        raise ReviewError(f"Unknown provider: {provider}")

    data = _extract_json(raw)

    # Fill in safe defaults in case the model omits a key despite instructions
    data.setdefault("language", "unknown")
    data.setdefault("explanation", "")
    data.setdefault("bugs", [])
    data.setdefault("optimized_code", code)

    return data