"""Shared Groq client + retry/backoff helper for Phase 2 scripts."""
import os
import re
import time

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "llama-3.3-70b-versatile"  # reserved for the "Ask the Reviews" chatbot (Phase 4)
TAGGING_MODEL = "llama-3.1-8b-instant"  # at-scale tagging: bounded-vocabulary classification
# doesn't need a 70B model, and its free-tier daily token budget is far less restrictive -
# llama-3.3-70b-versatile hit a 100,000 tokens/day (TPD) wall after ~190 tagged reviews during
# this project's Phase 2 execution; 8b-instant had not hit any daily wall after equivalent usage.
_client = None

# If Groq's error message says we need to wait longer than this to retry, it's the daily
# request/token quota talking, not a transient blip - stop and surface it instead of spinning.
MAX_SENSIBLE_WAIT_SECONDS = 300


class QuotaExhausted(Exception):
    """Raised when Groq reports a wait long enough that it's clearly the daily cap, not a blip."""


def _get_api_key():
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    try:  # Streamlit Community Cloud: secrets set via the dashboard, not a .env file
        import streamlit as st
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None


def client():
    global _client
    if _client is None:
        key = _get_api_key()
        if not key:
            raise RuntimeError("GROQ_API_KEY not set in .env (local) or st.secrets (deployed)")
        _client = Groq(api_key=key)
    return _client


def _parse_retry_after(msg):
    m = re.search(r"try again in (\d+(?:\.\d+)?)\s*s", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"try again in (\d+)m([\d.]+)s", msg, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    return None


def chat(messages, temperature=0, max_tokens=800, tries=5, response_format=None, model=None):
    kwargs = dict(model=model or MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if response_format:
        kwargs["response_format"] = response_format
    last_err = None
    for attempt in range(tries):
        try:
            resp = client().chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:  # groq raises various exception subtypes for 429/5xx
            last_err = e
            msg = str(e)
            retry_after = _parse_retry_after(msg)
            if retry_after is not None and retry_after > MAX_SENSIBLE_WAIT_SECONDS:
                raise QuotaExhausted(
                    f"Groq says to wait {retry_after:.0f}s ({retry_after / 3600:.1f}h) - "
                    f"this is the daily quota, not a transient error: {msg[:200]}"
                ) from e
            wait = retry_after if retry_after is not None else 2 * (attempt + 1)
            if "429" in msg or "rate" in msg.lower():
                wait = max(wait, 15 * (attempt + 1))
            print(f"    groq call failed (attempt {attempt + 1}/{tries}): {msg[:150]} - retrying in {wait:.0f}s")
            time.sleep(wait)
    raise RuntimeError(f"Groq call failed after {tries} attempts: {last_err}")
