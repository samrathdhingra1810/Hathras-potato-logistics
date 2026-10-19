"""Checks the Gemini key and model with one tiny request.

Usage (the key stays in your shell, never in the repo):
    GEMINI_API_KEY=your-key .venv/bin/python scripts/check_gemini.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portal import assistant  # noqa: E402

if not assistant.ai_configured():
    sys.exit("Set GEMINI_API_KEY first.")
out = assistant.answer_with_gemini([{"role": "user", "content": "In one sentence: will Hathras run short of cold storage?"}], {"page": "/"})
print("model:", assistant.MODEL)
print("tools used:", out["tools"])
print("reply:", out["reply"])
