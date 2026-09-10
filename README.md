# Baseera — Voice-Guided Object Finder

This turns the research notebook into two small, plain-Python apps:

- **`backend/`** — a **FastAPI** server that loads Whisper, YOLO and the LLM once, and exposes one endpoint (`/api/find`) that runs the whole pipeline.
- **`frontend/`** — a **Streamlit** app that gives users a page to type/record a question, upload or capture a photo, and hear the spoken answer. It just calls the FastAPI endpoint — no HTML/JS needed.

They run as two separate processes on your machine and talk over HTTP (`localhost:8000`).

## File hierarchy

```
baseera/
├── backend/
│   ├── main.py            # FastAPI app — the /api/find endpoint
│   ├── pipeline.py         # all AI logic, ported from the notebook (models load here, once)
│   └── requirements.txt
├── frontend/
│   ├── app.py               # Streamlit UI
│   └── requirements.txt
├── assets/
│   └── logo.png             # your logo, shown in the Streamlit header
├── run_backend.sh / .bat    # convenience start scripts
├── run_frontend.sh / .bat
├── .gitignore
└── README.md
```

Nothing here is Colab-specific — no `IN_COLAB` branches, no browser JS for camera/mic capture. The Streamlit `st.camera_input` and file uploaders replace that.

## How a request flows

1. User types or uploads a voice question, and uploads/takes a photo, in Streamlit.
2. Streamlit sends both to FastAPI's `POST /api/find` as a multipart form.
3. FastAPI: transcribes audio (if given) with Whisper → extracts the target object with the LLM → runs both YOLO models on the photo → estimates direction/distance → composes a spoken sentence with the LLM → synthesizes it with gTTS.
4. FastAPI returns JSON (`query_text`, `language`, `target_object`, `matches`, `reply_text`) plus the mp3 reply as base64.
5. Streamlit displays the text and plays the audio.

## One-time setup (VS Code)

1. Open the `baseera/` folder in VS Code.
2. Open a terminal (`` Ctrl+` ``) at the `baseera/` root and create **one shared virtual environment** for both apps:

   ```bash
   python -m venv venv
   ```

   Activate it:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. Install both sets of dependencies into it:

   ```bash
   pip install -r backend/requirements.txt
   pip install -r frontend/requirements.txt
   ```

   This step downloads PyTorch etc. and can take a while — that's normal.

## Running it

You need **two terminals**, both with `venv` activated, because the backend and frontend are two separate running processes.

**Terminal 1 — backend:**

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Wait until you see `All models loaded: [...]` — this is the point where Whisper/YOLO/the LLM actually download and load into memory. The first run will download the model weights, so it's slower; after that they're cached locally and startup is much faster.

Or just double-click / run `run_backend.sh` (Mac/Linux) or `run_backend.bat` (Windows) from the project root instead of the two commands above.

**Terminal 2 — frontend:**

```bash
cd frontend
streamlit run app.py
```

Or run `run_frontend.sh` / `run_frontend.bat`.

Streamlit will open `http://localhost:8501` in your browser automatically. The sidebar shows a green "Connected to backend" once it can reach FastAPI.

## Notes for the team

- **Models load once**, at backend startup — not per-request — so keep the backend terminal running while you use the app.
- **`--reload`** on uvicorn auto-restarts the server whenever you edit backend code, which is convenient while developing but will re-load all models each time it restarts — drop `--reload` if that gets annoying.
- **`FOCAL_LENGTH`** in `backend/pipeline.py` is a rough calibration constant carried over from the notebook — recalibrate it for whatever camera actually ends up in the product (measure a known object at a known distance and solve for focal length), same as noted in the notebook.
- CPU-only machines will work but the LLM + YOLO + Whisper calls will be noticeably slower than on a GPU box; if anyone on the team has a CUDA GPU, PyTorch will pick it up automatically (see `torch.cuda.is_available()` checks already in `pipeline.py`).
- If you later want to swap the local Qwen LLM for a cloud API, the only two functions that call it are `extract_object_local()` and `generate_voice_response()` in `backend/pipeline.py` — same as the notebook already notes.
- To deploy this beyond your own machines later (e.g. a shared demo link), the backend and frontend can be pushed as two separate services — but running both locally on one machine, as set up here, is enough for a working demo/handoff.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Streamlit sidebar says "Backend not reachable" | The FastAPI terminal isn't running, or crashed during model loading — check Terminal 1 for errors. |
| First request takes minutes | Normal on first run — model weights are downloading. Subsequent requests are much faster. |
| `Could not decode the uploaded image` | The uploaded file isn't a valid image — re-upload/retake the photo. |
| Arabic response comes back in English | The LLM's Arabic generation was rejected by the `_contains_arabic()` check and the hand-written template fallback kicked in — this is expected/by design, not a bug. |
