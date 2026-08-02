"""Shared data loading for the Streamlit app - dashboard and chatbot both read from here."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from common import RAW_DIR, find_quotes, read_jsonl  # noqa: E402,F401

PROCESSED_DIR = RAW_DIR.replace("/raw", "/processed")


def load_joined_tagged():
    """The app reads the small pre-joined export (see src/common.py dump_app_export), not the
    full 60MB+ cleaned corpus - keeps the deployed repo small and startup fast."""
    path = f"{PROCESSED_DIR}/app_export.jsonl"
    if not os.path.exists(path):
        return []
    return read_jsonl(path)


def load_pattern_tables():
    path = f"{PROCESSED_DIR}/pattern_tables.json"
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_phase1_summary():
    path = f"{RAW_DIR}/phase1_summary.json"
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


