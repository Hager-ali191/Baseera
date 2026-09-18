"""
Baseera FastAPI backend.

Run with:
    uvicorn main:app --reload --port 8000

(run this from inside the `backend/` folder, with your venv active)
"""

import base64
import json
import os
import tempfile
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import assistant  # Siara's brain — LLM Q&A about the project/site, no heavy model loading
import pipeline  # importing this triggers model loading (see pipeline.py)

app = FastAPI(title="Baseera API", version="1.0")

# Allows the Streamlit app (running on a different port) to call this API.
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


@app.post("/api/find")
async def find_object(
    image: UploadFile = File(..., description="Photo of the room/scene"),
    audio: UploadFile | None = File(None, description="Voice question (wav/mp3), optional"),
    text: str | None = Form(None, description="Typed question, used if no audio is sent"),
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
        return JSONResponse({"error": f"Pipeline failed: {e}"}, status_code=500)

    # Synthesize the spoken reply and send it back as base64 so the
    # frontend can play it directly with no extra file server needed.
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        audio_out_path = tmp.name
    try:
        pipeline.speak(result["reply_text"], language=result["language"], filename=audio_out_path)
        with open(audio_out_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    finally:
        os.remove(audio_out_path)

    result["audio_base64"] = audio_b64
    return result


# -----------------------------------------------------------------------------
# Siara — the in-app guide bot. Separate from the object-finding pipeline
# above: this endpoint answers questions ABOUT the project/website itself.
# -----------------------------------------------------------------------------
class ChatTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class AssistantRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []


@app.post("/api/assistant")
def ask_assistant(req: AssistantRequest):
    """
    Siara's chat endpoint. Uses Claude (if ANTHROPIC_API_KEY is set on the
    backend) to answer any question about how Baseera works or where to
    find something on the site; otherwise falls back to rule-based answers.
    See assistant.py for details.
    """
    if not req.message or not req.message.strip():
        return JSONResponse({"error": "message must not be empty."}, status_code=400)

    history = [{"role": t.role, "content": t.content} for t in req.history]
    return assistant.get_assistant_reply(req.message, history=history)


# -----------------------------------------------------------------------------
# Feedback form on the homepage. The frontend already posts here; this was
# previously missing on the backend, so every submission silently 404'd.
# Stored as a simple local JSON-lines file — swap for a real database/email
# integration later if needed, the frontend contract won't need to change.
# -----------------------------------------------------------------------------
# Deliberately stored OUTSIDE backend/ (one level up, in a "data/" folder at
# the project root) — not because it needs to be there, but because
# uvicorn --reload (if someone re-enables it — see run_backend.sh/.bat)
# watches backend/ recursively, and a file that changes on every submission
# would trigger a full model-reloading restart on every piece of feedback.
FEEDBACK_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "feedback_log.jsonl")
os.makedirs(os.path.dirname(FEEDBACK_LOG_PATH), exist_ok=True)


class FeedbackRequest(BaseModel):
    name: str = ""
    email: str = ""
    message: str


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    if not req.message or not req.message.strip():
        return JSONResponse({"error": "message must not be empty."}, status_code=400)

    entry = {
        "name": req.name.strip(),
        "email": req.email.strip(),
        "message": req.message.strip(),
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(FEEDBACK_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        return JSONResponse({"error": f"Could not save feedback: {e}"}, status_code=500)

    return {"status": "ok"}
