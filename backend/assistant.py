"""
Siara's brain.

This module powers the in-app assistant ("Siara") that can answer questions
about the Baseera *project* and *website* itself (not the object-finding
pipeline's user-facing queries — that's `pipeline.py`).

Siara uses the SAME local LLM `pipeline.py` already loads for the main
object-finding pipeline (Qwen2.5-Instruct by default, or whatever
BASEERA_LLM_MODEL is set to) — not a paid API. This means:
  - No API key, no signup, no cost, no internet connection needed for Siara.
  - No extra model loaded into memory — Siara reuses the one already
    sitting there for object extraction / reply phrasing, so she adds
    essentially zero extra RAM footprint on top of what's already running.
  - Answer quality follows whatever BASEERA_LLM_MODEL is set to. The default
    (Qwen2.5-0.5B-Instruct) is small and fast specifically to be gentle on
    modest hardware; if you have RAM to spare, raising BASEERA_LLM_MODEL
    (see backend/.env.example) improves both the main pipeline's answers
    AND Siara's, at the same time, since they share the model.

Two modes, chosen automatically:

1. LLM mode (default) — the question, a compact project-knowledge prompt,
   and recent chat history are sent to the local model. This means Siara
   can answer many different phrasings of a question about the project,
   not just a fixed set of keywords.

2. Fallback mode — used automatically if the LLM call fails for any reason,
   or if BASEERA_SIARA_LLM=off is set (e.g. to keep Siara as cheap/instant
   as possible on very constrained hardware, at the cost of only answering
   a fixed set of keyword-matched questions). Rule-based, always available,
   Siara never goes completely silent.
"""

import os
from typing import List, Optional, TypedDict

# Set BASEERA_SIARA_LLM=off to skip the local LLM entirely and always use
# the instant rule-based fallback below — e.g. if even the small local
# model is more CPU than you want Siara spending on a constrained machine.
SIARA_LLM_ENABLED = os.getenv("BASEERA_SIARA_LLM", "on").strip().lower() not in ("off", "0", "false")

# -----------------------------------------------------------------------------
# Kept deliberately short: this is fed to a small (by default ~0.5B
# parameter) local model, not a frontier one. Long, nuanced system prompts
# tend to get partially ignored by small models and just slow down every
# reply (the whole prompt gets re-processed on every turn). Keep this in
# sync with README.md at a high level, and with the keyword answers below.
# -----------------------------------------------------------------------------
PROJECT_KNOWLEDGE = """You are Siara, the short, friendly built-in guide for the Baseera project — a chat widget in the corner of the Baseera web app. Only answer questions about Baseera itself: what it is, how it works, or how to use this site. Keep answers to 1-3 short sentences.

WHAT BASEERA IS: An assistive-tech app that helps visually impaired users find everyday objects. A user asks a question (voice or typed, English or Arabic) and shows a photo of the room; Baseera speaks back the object's direction and distance.

HOW IT WORKS: Backend (FastAPI) transcribes voice with Whisper, detects language, uses a local LLM to find the target object name, runs two YOLOv8 models on the photo, computes direction/distance, and has the LLM phrase one spoken reply (gTTS). Endpoints: GET /health, POST /api/find (main pipeline), POST /api/assistant (that's you).

PAGES: "/" Home (architecture overview, team, feedback form). "/about" About (mission, who it's for, FAQ). "/demo" Live Demo — record voice (mic button, click to start/stop) or upload audio or type a question; capture a photo (live camera + Snap button, or upload); "SEE DASHBOARD RESULTS" button sends it all and shows the answer right there.

TROUBLESHOOTING: Backend not reachable = it's not running or still loading models (uvicorn main:app --port 8000, no --reload). Mic/camera not working = browser needs permission. Arabic answer showing in English = safety fallback, not a bug. Slow/hot machine = set BASEERA_CPU_THREADS lower.

If asked something unrelated to Baseera, say that's outside what you help with here. Never invent features that aren't listed above."""

FALLBACK_KNOWLEDGE_BASE = {
    "tools": "Baseera is built using FastAPI for the backend, NiceGUI (and a Streamlit alternative) for the web interface, YOLOv8 for object detection, Faster-Whisper for speech-to-text, a small local instruct LLM (Qwen2.5, size configurable via BASEERA_LLM_MODEL) for language understanding, and gTTS for the spoken replies.",
    "yolo": "Baseera runs two YOLOv8 models (yolov8n and yolov8s) via backend/pipeline.py to detect everyday objects and estimate their direction and distance from a single photo.",
    "audio": "Voice input is transcribed with Faster-Whisper, and replies are spoken back using gTTS. On the Input page, you can either record your voice live or upload an audio file.",
    "api": "The FastAPI backend runs on port 8000 by default, exposing GET /health, POST /api/find (the main pipeline), and POST /api/assistant (that's me!).",
    "creator": "Baseera is an assistive-technology project built to help visually impaired users locate everyday objects using voice and a camera.",
    "pages": "The app has three pages: Home (architecture overview, team, and a feedback form), About (the project's mission and FAQ), and the Live Demo (record/upload voice + capture/upload a photo, then see the results right on the same page).",
    "test": "You can run the automated test suite with `pytest backend/tests -v` from the project root. It covers the pipeline's core logic and the API endpoints, and stubs the heavy ML libraries so it runs quickly.",
    "recording": "To ask by voice, go to the Live Demo page and press the microphone button under 'Voice Command Input' — your browser will ask for microphone permission the first time. You can also upload an audio file, or just type your question.",
}


def _fallback_reply(user_query: str) -> str:
    query = user_query.lower()
    if any(k in query for k in ("tool", "tech", "stack", "built", "made with")):
        return FALLBACK_KNOWLEDGE_BASE["tools"]
    if any(k in query for k in ("yolo", "detect", "vision", "camera")):
        return FALLBACK_KNOWLEDGE_BASE["yolo"]
    if any(k in query for k in ("audio", "voice", "whisper", "speak", "mic", "record")):
        return FALLBACK_KNOWLEDGE_BASE["recording"]
    if any(k in query for k in ("api", "backend", "endpoint", "port")):
        return FALLBACK_KNOWLEDGE_BASE["api"]
    if any(k in query for k in ("who", "creator", "author", "purpose", "why", "mission")):
        return FALLBACK_KNOWLEDGE_BASE["creator"]
    if any(k in query for k in ("page", "where is", "find", "navigate", "section")):
        return FALLBACK_KNOWLEDGE_BASE["pages"]
    if any(k in query for k in ("test", "pytest")):
        return FALLBACK_KNOWLEDGE_BASE["test"]
    return (
        "Hi! I'm Siara. I can help you explore how Baseera works — try asking "
        "about the tech stack, the API, voice recording, YOLO detection, "
        "testing, or which page has what you're looking for."
    )


class ChatTurn(TypedDict):
    role: str  # "user" or "assistant"
    content: str


def get_assistant_reply(message: str, history: Optional[List[ChatTurn]] = None) -> dict:
    """
    Returns {"reply": str, "source": "llm" | "fallback"}.

    Tries the local LLM first (unless disabled via BASEERA_SIARA_LLM=off);
    falls back to rule-based answers on any failure so the widget always
    responds to something.
    """
    history = history or []

    if SIARA_LLM_ENABLED:
        try:
            import pipeline  # the already-loaded local LLM — see module docstring

            # Keep only the last couple of turns: this model re-processes the
            # whole prompt on every call (no persistent conversation state),
            # so a shorter prompt means a faster reply on CPU.
            messages = [{"role": "system", "content": PROJECT_KNOWLEDGE}]
            for turn in history[-4:]:
                messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": message})

            outputs = pipeline.llm_pipeline(
                messages,
                max_new_tokens=200,
                do_sample=True,
                temperature=0.6,
            )
            reply = outputs[0]["generated_text"][-1]["content"].strip()
            if reply:
                return {"reply": reply, "source": "llm"}
        except Exception:
            # Any failure (model not ready yet, out of memory, unexpected
            # output shape...) falls straight through to the fallback below.
            pass

    return {"reply": _fallback_reply(message), "source": "fallback"}
