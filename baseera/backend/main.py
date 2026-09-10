"""
Baseera FastAPI backend.

Run with:
    uvicorn main:app --reload --port 8000

(run this from inside the `backend/` folder, with your venv active)
"""

import base64
import os
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
