"""
Groq API client with exponential backoff and JSON parsing.
All LLM calls in MediFind go through this module.
"""
from __future__ import annotations

import os
import json
import time
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


DEFAULT_MODEL = "llama-3.3-70b-versatile"
_requests_per_min: int = int(os.getenv("GROQ_REQUESTS_PER_MINUTE", "28"))
_interval: float = 60.0 / _requests_per_min


def call_groq(
    prompt: str,
    system: str = "You are a precise JSON-outputting assistant. Output ONLY valid JSON, no markdown, no explanation.",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1500,
    temperature: float = 0.1,
    retries: int = 5,
    expect_json: bool = True,
) -> str:
    """
    Call Groq with exponential backoff on rate-limit (429) errors.
    Returns the raw string content.
    """
    client = get_client()
    for attempt in range(retries):
        try:
            kwargs: dict = dict(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if expect_json:
                kwargs["response_format"] = {"type": "json_object"}

            resp = client.chat.completions.create(**kwargs)
            time.sleep(_interval)  # respect rate limit
            return resp.choices[0].message.content or ""

        except Exception as exc:
            if "429" in str(exc) or "rate_limit" in str(exc).lower():
                wait = (2 ** attempt) + 2
                print(f"[Groq] Rate limited. Waiting {wait}s… (attempt {attempt+1}/{retries})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Groq max retries exceeded")


def call_groq_json(prompt: str, **kwargs) -> dict:
    """Call Groq and parse JSON response. Returns empty dict on parse failure."""
    raw = call_groq(prompt, expect_json=True, **kwargs)
    # Strip markdown code fences if present
    raw = re.sub(r"```json\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```\s*$", "", raw)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"[Groq] JSON parse error: {e}\nRaw: {raw[:200]}")
        return {}
