"""
Baseera FastAPI backend.

Run with:
    uvicorn main:app --port 8000

Deliberately NOT --reload: this backend loads Whisper + YOLO + a local LLM
once at startup (a minute or more), and it also writes files into this same
folder while running (downloaded model weights). --reload watches this
whole folder for changes, so those writes were triggering full automatic
restarts mid-request — every in-flight request failed with a connection
error while everything reloaded. Restart manually after editing code, or
use `--reload --reload-exclude "*.pt"` if you really want it.
"""

import base64
import os
import sqlite3
import tempfile
from datetime import datetime

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import assistant  # Siara's brain — LLM Q&A about the project/site, no heavy model loading
import pipeline  # importing this triggers model loading (see pipeline.py)

app = FastAPI(title="Baseera API", version="1.0")

# Database setup for feedback.
#
# Deliberately stored OUTSIDE backend/ (one level up, in a "data/" folder at
# the project root) rather than at "feedback.db" in the current directory.
# uvicorn --reload watches backend/ recursively, and sqlite writes to a file
# inside that folder on every single feedback submission — each write looks
# like a code change to --reload, which kills and fully restarts the server
# (reloading every AI model, ~1 minute) mid-request. Moving the DB file out
# of the watched folder avoids that entirely, whether or not --reload is on.
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "feedback.db")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """
        )
        conn.commit()


init_db()


class FeedbackRequest(BaseModel):
    name: str
    email: str
    message: str


# Allows the NiceGUI frontend to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Simple check that the server is up and models are loaded."""
    return {"status": "ok", "models": list(pipeline.detection_models.keys())}


@app.post("/api/feedback")
def submit_feedback(data: FeedbackRequest):
    """Endpoint to submit user feedback."""
    if not data.name.strip() or not data.email.strip() or not data.message.strip():
        return JSONResponse(
            {"error": "All fields are required."}, status_code=400
        )

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (name, email, message, timestamp) VALUES (?, ?, ?, ?)",
            (
                data.name.strip(),
                data.email.strip(),
                data.message.strip(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    return {"status": "success", "message": "Feedback received successfully."}


@app.get("/api/feedback")
def get_feedback():
    """Endpoint to retrieve submitted feedback."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, message, timestamp FROM feedback ORDER BY id DESC"
        )
        rows = cursor.fetchall()

    feedback_list = [
        {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "message": row[3],
            "timestamp": row[4],
        }
        for row in rows
    ]
    return {"feedback": feedback_list}


@app.post("/api/find")
async def find_object(
    image: UploadFile = File(..., description="Photo of the room/scene"),
    audio: UploadFile | None = File(
        None, description="Voice question (wav/mp3), optional"
    ),
    text: str | None = Form(
        None, description="Typed question, used if no audio is sent"
    ),
    conf: float = Form(0.3, description="YOLO confidence threshold, 0-1"),
):
    if audio is None and not text:
        return JSONResponse(
            {"error": "Send either an 'audio' file or a 'text' field."},
            status_code=400,
        )

    image_bytes = await image.read()
    try:
        frame = pipeline.load_image_from_bytes(image_bytes)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    audio_bytes = await audio.read() if audio is not None else None

    try:
        result = pipeline.run_full_pipeline(
            frame=frame,
            audio_bytes=audio_bytes,
            query_text=text,
            conf=conf,
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Pipeline failed: {e}"}, status_code=500
        )

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        audio_out_path = tmp.name
    try:
        pipeline.speak(
            result["reply_text"],
            language=result["language"],
            filename=audio_out_path,
        )
        with open(audio_out_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    finally:
        os.remove(audio_out_path)

    result["audio_base64"] = audio_b64
    return result


# -----------------------------------------------------------------------------
# Siara — the in-app guide bot. Separate from the object-finding pipeline
# above: this endpoint answers questions ABOUT the project/website itself.
# Lightweight — no heavy models loaded for this, just an optional call to
# Claude (or a rule-based fallback if no ANTHROPIC_API_KEY is set). See
# assistant.py for details.
# -----------------------------------------------------------------------------
class ChatTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class AssistantRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []


@app.post("/api/assistant")
def ask_assistant(req: AssistantRequest):
    if not req.message or not req.message.strip():
        return JSONResponse({"error": "message must not be empty."}, status_code=400)

    history = [{"role": t.role, "content": t.content} for t in req.history]
    return assistant.get_assistant_reply(req.message, history=history)