"""
Siara's brain.

This module powers the in-app assistant ("Siara") that can answer questions
about the Baseera *project* and *website* itself (not the object-finding
pipeline's user-facing queries — that's `pipeline.py`).

Two modes, chosen automatically:

1. LLM mode (preferred) — if ANTHROPIC_API_KEY is set, every question is sent
   to Claude along with a system prompt describing the whole project (what it
   is, how it's built, every page and what's on it, common troubleshooting).
   This means Siara can answer *any* phrasing of *any* question about the
   project, not just a fixed set of keywords, and can help someone who says
   "I can't find X" by pointing at the right page/button.

2. Fallback mode — if no API key is configured (or the API call fails for
   any reason, e.g. no internet), Siara falls back to the same rule-based
   keyword matching the project shipped with originally, so the guide bot
   never goes completely silent.

Set the key as an environment variable before starting the backend:

    export ANTHROPIC_API_KEY=sk-ant-...          # macOS/Linux
    setx ANTHROPIC_API_KEY "sk-ant-..."           # Windows

Optionally override the model with ANTHROPIC_MODEL (defaults to a small,
fast, cheap model since this is a lightweight Q&A bot, not the main pipeline).
"""

import os
from typing import List, Optional, TypedDict

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# -----------------------------------------------------------------------------
# Everything Siara needs to know about the project, in one place.
# Keep this in sync with README.md — this IS the bot's "training data" for
# LLM mode, and the ordering of the keyword checks below for fallback mode.
# -----------------------------------------------------------------------------
PROJECT_KNOWLEDGE = """
You are Siara, the friendly built-in guide for the Baseera project. You live
as a small floating chat widget in the corner of the Baseera web app and your
only job is to help the person using the app or reading about the project.

WHAT BASEERA IS
Baseera ("insight" in Arabic) is an AI-powered voice-guided assistant built to
help visually impaired users locate everyday objects around them. A user asks
a question out loud or by typing (e.g. "where is my laptop?" or the Arabic
equivalent), shows the app a photo of the room (camera or upload), and
Baseera speaks back the object's approximate direction and distance.

ARCHITECTURE (two independent parts talking over HTTP)
- Backend: a FastAPI server (`backend/`) that loads all AI models once at
  startup and exposes a few endpoints:
    * GET  /health        - liveness check, lists loaded detection models
    * POST /api/find       - the core pipeline: takes a photo + (voice or
                              typed question), returns text + spoken (mp3)
                              answer
    * POST /api/assistant  - this Q&A endpoint that powers Siara herself
  Under the hood it chains together: Faster-Whisper (speech-to-text),
  a local Qwen2.5-1.5B-Instruct LLM (to pull the target object out of the
  question and to phrase the final spoken sentence), two YOLOv8 models
  (object detection), a simple pinhole-camera distance estimate, and gTTS
  (text-to-speech).
- Frontend: there are two, either can be used against the same backend:
    * NiceGUI app (`NiceGUI/app.py` + `NiceGUI/pages/`) — the primary, richer
      web UI, split into one file per page: Home, About, and Live Demo.
      Siara (you) lives here as a floating widget on every page.
    * Streamlit app (`Streamlit/app.py`) — a simpler, single-page
      alternative UI, handy for quick demos.

HOW A REQUEST FLOWS THROUGH THE MAIN PIPELINE
1. User records/uploads audio, or types a question, and provides a photo.
2. The frontend posts both to POST /api/find on the backend.
3. Backend transcribes audio with Whisper (skipped if the user typed instead),
   detects the language (English/Arabic supported), extracts the target
   object name with the LLM, runs both YOLO models on the photo, works out
   direction (e.g. "top-left") and rough distance in meters for any matches,
   and asks the LLM to phrase one short spoken sentence with the answer.
4. Backend returns JSON with query_text, language, target_object, a list of
   matches (each with object/direction/distance_m/confidence/model), and
   reply_text, plus the spoken answer as a base64 mp3.
5. The frontend displays the text and plays the audio.

NICEGUI PAGES AND WHERE THINGS ARE
- "/" Home (`pages/home.py`) — hero section, a System Architecture &
  Pipeline overview, the team, special thanks, and a project feedback form
  at the bottom (posts to POST /api/feedback).
- "/about" About (`pages/about.py`) — the project's mission, who it's for,
  the feature list, and an FAQ. If someone asks "what is this project" or
  "who is this for", point them here.
- "/demo" Live Demo (`pages/demo.py`) — the interactive workspace:
  Section 1 lets them record their voice question live with a real
  microphone recorder (click once to start, again to stop) or upload an
  audio file, or type the question instead. Section 2 lets them use a live
  webcam preview + "Snap Camera Frame" button, or upload a photo file
  instead. The big button at the bottom ("SEE DASHBOARD RESULTS") sends
  everything to the backend and shows the transcribed question, the spoken
  reply, direction, distance, and confidence right there on the same page.
- You (Siara) float in the bottom-left corner on every page. You can answer
  questions in text or the person can talk to you (their browser's speech
  recognition fills in the chat box) and you can read your answers aloud
  (browser text-to-speech).

TROUBLESHOOTING PEOPLE OFTEN ASK ABOUT
- "Backend not reachable" — the FastAPI server isn't running, or it's still
  loading models. Start it with `uvicorn main:app --reload --port 8000` from
  inside `backend/`, and wait for the console line "All models loaded".
  First run also downloads model weights, so it's slow the first time.
  Ensure BACKEND_URL (frontend env var) matches wherever it's actually
  running, default is http://127.0.0.1:8000.
- Mic recording doesn't seem to do anything — the browser needs microphone
  permission; check the address bar for a blocked-permission icon. Recording
  requires a secure context (localhost is fine; a plain http:// address on
  another machine is not — use https or an SSH tunnel).
- "Could not decode the uploaded image" — the uploaded file isn't a valid
  image; re-upload or retake the photo.
- Arabic response comes back in English — this is a deliberate safety net:
  if the LLM's Arabic generation doesn't actually contain Arabic characters,
  the backend falls back to a hand-written Arabic template instead of
  returning broken/English text.
- Distance numbers look off — FOCAL_LENGTH in backend/pipeline.py is a rough
  constant that should be recalibrated for whatever camera is actually used
  (measure a known object at a known distance and solve for focal length).
- Running tests — `pytest backend/tests -v` from the project root (with the
  backend's virtual environment active). The test suite stubs out the heavy
  ML libraries so it runs in seconds without downloading any model weights.

HOW TO ANSWER
- Be concise and warm. This is a floating chat widget, not a document —
  answer in a few sentences, not an essay, unless the person clearly wants
  detail.
- Only answer questions about the Baseera project, this website/app, how to
  use it, its architecture, setup, or troubleshooting. If asked something
  totally unrelated (weather, unrelated coding help, etc.), gently say
  that's outside what you can help with here and steer back to Baseera.
- If someone says they can't find a feature, tell them exactly which page
  and section it's on, using the page names above.
- Never invent API endpoints, files, or behavior that isn't described above.
  If you don't know, say so plainly and suggest checking the README.
- Keep to English, since that's the language of this assistant.
""".strip()

FALLBACK_KNOWLEDGE_BASE = {
    "tools": "Baseera is built using FastAPI for the backend, NiceGUI (and a Streamlit alternative) for the web interface, YOLOv8 for object detection, Faster-Whisper for speech-to-text, a local Qwen2.5-1.5B-Instruct LLM for language understanding, and gTTS for the spoken replies.",
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
        "testing, or which page has what you're looking for. "
        "(I'm currently running in offline mode — set ANTHROPIC_API_KEY on "
        "the backend for full conversational answers.)"
    )


class ChatTurn(TypedDict):
    role: str  # "user" or "assistant"
    content: str


def get_assistant_reply(message: str, history: Optional[List[ChatTurn]] = None) -> dict:
    """
    Returns {"reply": str, "source": "llm" | "fallback"}.

    Tries the real LLM first (if configured); falls back to rule-based
    answers on any failure so the widget always responds to something.
    """
    history = history or []
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            messages = [{"role": t["role"], "content": t["content"]} for t in history]
            messages.append({"role": "user", "content": message})

            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=400,
                system=PROJECT_KNOWLEDGE,
                messages=messages,
            )
            text = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            ).strip()
            if text:
                return {"reply": text, "source": "llm"}
        except Exception:
            # Any failure (missing package, bad key, network, rate limit...)
            # falls straight through to the offline fallback below.
            pass

    return {"reply": _fallback_reply(message), "source": "fallback"}
