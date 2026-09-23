"""
Siara's brain.

This module powers the in-app assistant ("Siara") using the Groq API
(llama-3.1-8b-instant model) to answer questions about the Baseera project and website.
"""

import os
from typing import List, Optional, TypedDict
from fastapi import APIRouter
from pydantic import BaseModel

try:
    from groq import Groq
except ImportError:
    Groq = None

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()

PROJECT_KNOWLEDGE = """You are Siara, the short, friendly built-in guide for the Baseera project — a chat widget in the corner of the Baseera web app. Only answer questions about Baseera itself: what it is, how it works, or how to use this site. Keep answers to 1-3 short sentences.

WHAT BASEERA IS: An assistive-tech app that helps visually impaired users find everyday objects. A user asks a question (voice or typed, English or Arabic) and shows a photo of the room; Baseera speaks back the object's direction and distance.

HOW IT WORKS: Backend (FastAPI) transcribes voice with Whisper, detects language, uses an LLM to find the target object name, runs YOLOv8 models on the photo, computes direction/distance, and phrases one spoken reply (gTTS). Endpoints: GET /health, POST /api/find (main pipeline), POST /api/assistant (that's you).

PAGES: "/" Home (architecture overview, team, feedback form). "/about" About (mission, who it's for, FAQ). "/demo" Live Demo — record voice (mic button, click to start/stop) or upload audio or type a question; capture a photo (live camera + Snap button, or upload); "SEE DASHBOARD RESULTS" button sends it all and shows the answer right there.

TROUBLESHOOTING: Backend not reachable = it's not running or still loading models (uvicorn main:app --port 8000, no --reload). Mic/camera not working = browser needs permission. Arabic answer showing in English = safety fallback, not a bug. Slow/hot machine = set BASEERA_CPU_THREADS lower.

If asked something unrelated to Baseera, say that's outside what you help with here. Never invent features that aren't listed above."""

FALLBACK_KNOWLEDGE_BASE = {
    "tools": "Baseera is built using FastAPI for the backend, NiceGUI for the web interface, YOLOv8 for object detection, Faster-Whisper for speech-to-text, Groq (Llama 3.1) for language understanding, and gTTS for spoken replies.",
    "yolo": "Baseera runs YOLOv8 models via backend/pipeline.py to detect everyday objects and estimate their direction and distance from a single photo.",
    "audio": "Voice input is transcribed with Faster-Whisper, and replies are spoken back using gTTS. On the Live Demo page, you can either record your voice live or upload an audio file.",
    "api": "The FastAPI backend runs on port 8000 by default, exposing GET /health, POST /api/find (the main pipeline), and POST /api/assistant (that's me!).",
    "creator": "Baseera is an assistive-technology project built to help visually impaired users locate everyday objects using voice and a camera.",
    "pages": "The app has three pages: Home (architecture overview, team, and a feedback form), About (the project's mission and FAQ), and Live Demo (record/upload voice + capture/upload a photo).",
    "test": "You can run the automated test suite with `pytest backend/tests -v` from the project root.",
    "recording": "To ask by voice, go to the Live Demo page and press the microphone button under 'Voice Command Input'.",
}


def _fallback_reply(user_query: str) -> str:
    query = user_query.lower()
    if any(k in query for k in ("tool", "tech", "stack", "built", "made with")):
        return FALLBACK_KNOWLEDGE_BASE["tools"]
    if any(k in query for k in ("yolo", "detect", "vision", "camera")):
        return FALLBACK_KNOWLEDGE_BASE["yolo"]
    if any(k in query for k in ("audio", "voice", "whisper", "speak", "mic", "record")):
        return FALLBACK_KNOWLEDGE_BASE["audio"]
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
    role: str
    content: str


def get_assistant_reply(message: str, history: Optional[List[ChatTurn]] = None) -> dict:
    """
    Returns {"reply": str, "source": "groq" | "fallback"}.
    """
    history = history or []
    api_key = os.getenv("GROQ_API_KEY", "").strip() or GROQ_API_KEY

    if api_key and Groq is not None:
        try:
            client = Groq(api_key=api_key)
            messages = [{"role": "system", "content": PROJECT_KNOWLEDGE}]
            for turn in history[-4:]:
                messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": message})

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=200,
                temperature=0.6,
            )
            reply = response.choices[0].message.content.strip()
            if reply:
                return {"reply": reply, "source": "groq"}
        except Exception as e:
            print(f"[DEBUG - BACKEND ERROR] Groq API error: {e}", flush=True)

    return {"reply": _fallback_reply(message), "source": "fallback"}


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatTurn]] = None


@router.post("/api/assistant")
async def chat_assistant(req: ChatRequest):
    return get_assistant_reply(req.message, req.history)