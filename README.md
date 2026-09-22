<p align="center">
  <img src="assets/logo.png" width="140" alt="Baseera logo">
</p>

<h1 align="center">Baseera — Voice-Guided Object Finder</h1>

<p align="center">
  <i>"Baseera" (بصيرة) means <b>insight</b> — helping people see what a camera sees.</i>
</p>

---

## Table of Contents

- [1. What Baseera Is](#what-baseera-is)
- [2. How It Works, In Plain Terms](#how-it-works-in-plain-terms)
- [3. Project Structure](#project-structure)
- [4. The Backend](#the-backend)
- [5. The Frontend](#the-frontend)
- [6. Siara, the Guide Bot](#siara-the-guide-bot)
- [7. One-Time Setup](#one-time-setup)
- [8. Running the Project](#running-the-project)
- [9. Running with Docker](#running-with-docker)
- [10. Testing](#testing)
- [11. Troubleshooting](#troubleshooting)
- [12. Notes for Contributors](#notes-for-contributors)
- [13. Meet The Team](#👥-meet-the-team)

---

## What Baseera Is

Baseera is an **assistive-technology project**: an AI-powered voice-guided
assistant that helps **visually impaired users locate everyday objects**
around them, independently.

Instead of asking someone else "where did I put my keys?", a user asks
Baseera out loud (or types the question), shows it a photo of the room via
camera or upload, and Baseera speaks back where the object is — direction
and approximate distance — in a natural sentence, in **English or Arabic**.

**Who it's for:** primarily blind and low-vision users, but it's just as
useful for anyone in a low-visibility situation, or anyone who'd rather ask
than search.

**What it does, end to end:**
- Understands a spoken or typed question, in English or Arabic
- Detects everyday objects in a photo (laptop, phone, keys, cup, and more)
- Estimates the object's direction (e.g. "top-left") and distance in meters
- Speaks the answer back as a natural sentence
- Includes **Siara**, a built-in guide bot that can answer questions about
  the project itself and help you find your way around the site

**What it deliberately doesn't do:** store your voice or photos anywhere.
Every request is processed in memory and discarded once the response is
sent back. The Live Demo's run history (see §5) follows the same rule: it is
held in the browser tab's memory only, never written to disk, and disappears
when the page is reloaded.

## 2. How It Works, In Plain Terms

1. You ask a question — by voice or by typing — and show Baseera a photo
   of the room.
2. If you spoke, Baseera transcribes it (Whisper) and figures out what
   language it's in.
3. A small local language model reads your question and pulls out *what*
   you're looking for (e.g. "laptop").
4. Two object-detection models scan the photo for that object.
5. If found, Baseera works out roughly which direction it's in and how far
   away it is, using its position and size in the photo.
6. The same language model composes one short, natural spoken sentence
   with the answer, which is converted to speech and played back.

If you want the engineering detail behind each of those steps, see
[§4 The Backend](#4-the-backend) below — this section is deliberately kept
non-technical for anyone evaluating the *project*, not the code.

## Project Structure

```
Baseera/
├── backend/                  # FastAPI server — all the AI logic lives here
│   ├── main.py                 # API routes: /health, /api/find, /api/assistant, /api/feedback
│   ├── pipeline.py             # Whisper + YOLO + LLM + gTTS pipeline (loads once, at startup)
│   ├── assistant.py            # Siara's brain: LLM Q&A about the project, with offline fallback
│   ├── requirements.txt
│   ├── .env.example            # Optional ANTHROPIC_API_KEY for Siara's full LLM mode
│   ├── Dockerfile
│   ├── .dockerignore
│   └── tests/                  # Automated test suite (see §10)
│       ├── conftest.py
│       ├── test_pipeline.py
│       └── test_api.py
├── NiceGUI/                  # Primary web frontend — one file per page
│   ├── app.py                  # Entry point: imports pages/ (registers routes) + starts the server
│   ├── config.py                # BACKEND_URL, shared constants
│   ├── state.py                  # Shared AppState (last captured image/audio/results)
│   ├── styles.py                  # Global CSS/fonts
│   ├── layout.py                   # Sticky header — same component, used on every page
│   ├── guide_bot.py                 # Siara: floating chat + voice widget, used on every page
│   ├── feedback.py                   # Feedback form component (posts to /api/feedback)
│   ├── recording.py                   # Real mic recording + webcam capture (browser JS + glue)
│   ├── history.py                      # Live Demo run history: annotated photo + detection details per run
│   ├── pages/
│   │   ├── home.py                      # "/"      — hero, architecture, team, feedback
│   │   ├── about.py                      # "/about" — mission, audience, FAQ
│   │   └── demo.py                       # "/demo"  — the interactive workspace
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── Streamlit/                # Alternative, simpler single-page frontend
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── assets/
│   └── logo.png
├── data/
│   └── feedback_log.jsonl    # created on first feedback submission, not committed
├── docker-compose.yml         # Orchestrates backend + NiceGUI (Streamlit optional, see §9)
├── .env.example                # Optional ANTHROPIC_API_KEY, read by docker compose
├── run_backend.sh / .bat
├── run_frontend_nicegui.sh / .bat
├── run_frontend_streamlit.sh / .bat
└── README.md
```

Every page module registers itself with `@ui.page(...)` just by being
imported — `NiceGUI/app.py` imports `pages/home.py`, `pages/about.py`, and
`pages/demo.py` for exactly that side effect, then starts the server. To add
a new page: create `pages/your_page.py` with its own `@ui.page("/your-path")`
function (call `render_global_styles()`, `render_sticky_header(page="...")`,
and `init_guide_bot()` at the top, same as the others), then import it in
`app.py`.

The backend is completely frontend-agnostic: either frontend (or your own)
talks to it over plain HTTP, so you can run just one frontend, both, or swap
in something else entirely without touching the backend.

## The Backend

**Stack:** FastAPI · Faster-Whisper (speech-to-text) · two YOLOv8 models
(object detection) · a local Qwen2.5-1.5B-Instruct LLM (language
understanding + phrasing replies) · gTTS (text-to-speech) · Anthropic Claude
(optional, powers Siara's full conversational mode).

**Design choice worth knowing:** importing `pipeline.py` triggers all model
loading immediately, at process startup — not per-request. This means the
first startup is slow (weights download and load into memory), but every
request after that is fast, since nothing reloads.

### Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check; lists which detection models are loaded |
| `/api/find` | POST | The core pipeline — see request/response below |
| `/api/assistant` | POST | Siara's chat endpoint (project/site Q&A — see §6) |
| `/api/feedback` | POST | Homepage feedback form: `{name, email, message}` → appended to `data/feedback_log.jsonl` (project root, not inside `backend/` — see §11) |

**`POST /api/find`** — multipart form:

| Field | Type | Required | Notes |
|---|---|---|---|
| `image` | file | ✅ | Photo of the room/scene |
| `audio` | file | if no `text` | Voice question (wav/mp3/webm) |
| `text` | string | if no `audio` | Typed question, used only if no audio is sent |
| `conf` | float | ❌ (default `0.3`) | YOLO confidence threshold, 0–1 |

Response:

```json
{
  "query_text": "where is my laptop",
  "language": "en",
  "target_object": "laptop",
  "matches": [
    {"object": "laptop", "direction": "left", "distance_m": 1.2, "confidence": 0.91, "model": "yolov8n", "bbox": [112, 240, 688, 655]}
  ],
  "reply_text": "Yes, I found your laptop. It is located to the left, about 1.2 meters away.",
  "audio_base64": "<mp3 bytes, base64-encoded>"
}
```

Each match's `bbox` is `[x1, y1, x2, y2]` in pixels of the uploaded photo
(top-left and bottom-right corners of the detected box). The Live Demo's run
history uses it to draw the box on the photo.

**`POST /api/assistant`** — JSON:

```json
{ "message": "how do I use the camera?", "history": [ {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."} ] }
```

Response: `{ "reply": "...", "source": "llm" | "fallback" }`. See §6.

## The Frontend

There are **two** frontends, either one works against the same backend —
pick whichever fits your demo/deployment:

### NiceGUI (primary, recommended)

Split into one file per page under `NiceGUI/pages/` (see §3), sharing a
common header, styles, shared state, and the Siara widget:

- **Home** (`/`) — hero section, system architecture overview, team, and a
  project feedback form (posts to `POST /api/feedback` on the backend — see
  §11 for what was wrong with this before).
- **About** (`/about`) — the project's mission, who it's for, the full
  feature list, and an FAQ. This is where "what even is this project"
  questions get answered, separate from the more technical Home sections.
- **Live Demo** (`/demo`) — the interactive workspace:
  - *1. Voice Command Input:* ask by voice with a **real microphone
    recorder** (the browser's `MediaRecorder` API — click once to start,
    again to stop). This is a rewritten, verified implementation — see §11
    for exactly what was silently broken in the previous version. You can
    also upload an audio file, or just type the question as a fallback.
  - *2. Camera & Image Input:* a **live webcam preview** with a capture
    button (`getUserMedia` + a canvas snapshot), or upload a photo file.
  - One button ("SEE DASHBOARD RESULTS") sends everything to
    `POST /api/find` and shows the transcribed question, the spoken answer
    (auto-playing audio), and direction/distance/confidence for every
    match — read directly from the backend's real response shape.
  - *3. Run History* (`history.py`): every run in the current session is
    listed below the results, newest first (last 20 kept). Each entry is
    expandable and shows the photo with a **labelled bounding box on every
    detected match**, the transcribed question, language, target class,
    response time, the assistant's reply (with audio replay), and a table
    of confidence / direction / distance / model / box coordinates. Runs
    where the target class wasn't detected are recorded too. The history
    lives in that browser tab's memory only — nothing is saved to disk — so
    it clears on page reload, or with the "Clear history" button.
- **Siara** floats in the bottom-left corner on **every** page — one shared
  component (`guide_bot.py`), not copy-pasted per page.
- The **header** is also shared (`layout.py`) and now stays visible on
  every page. Previously it only faded in after scrolling past a threshold
  tuned for the long Home page, so shorter pages (About, Live Demo) could
  be scrolled through entirely without it ever appearing — see §11.

Run it: `run_frontend_nicegui.sh` / `.bat`, or `python NiceGUI/app.py` from
inside `NiceGUI/` with your venv active. Opens on `http://localhost:8080`.

### Streamlit (simpler alternative)

A single page: pick a question input mode (type it, or record with
`st.audio_input`, which is a real, working browser mic recorder built into
Streamlit), pick an image input mode (upload or `st.camera_input`), click
"Find it". Good for a quick demo without the multi-page structure.

Run it: `run_frontend_streamlit.sh` / `.bat`, or `streamlit run Streamlit/app.py`.
Opens on `http://localhost:8501`.

Both frontends read the backend URL from the `BACKEND_URL` environment
variable (defaults to `http://127.0.0.1:8000`), so pointing either one at a
backend running elsewhere is a one-line change, not a code edit.

## Siara, the Guide Bot

Siara is the floating assistant in the corner of the NiceGUI app. She's
**separate from the main object-finding pipeline** — her job is to answer
questions about the *project and website itself*, and to help if you can't
find something ("where's the camera input?", "how does distance get
calculated?", "what happens to my photo afterwards?").

**Two ways to talk to her, both in English:**
- **Chat** — type in the box.
- **Voice** — press the mic button; your browser's built-in speech
  recognition (Web Speech API) transcribes what you say. Toggle the speaker
  icon to have her read replies aloud too (speech synthesis, also
  browser-native — no extra backend calls or cost for the voice loop
  itself).

**Two ways she answers, chosen automatically by the backend:**
- **LLM mode** (full capability) — if `ANTHROPIC_API_KEY` is set on the
  backend (see `backend/.env.example`), every message goes to Claude along
  with a system prompt describing the entire project: architecture, every
  page and what's on it, common troubleshooting. This means she can answer
  *any* phrasing of *any* question about Baseera, not just fixed keywords.
- **Fallback mode** (always available) — without a key, or if the API call
  fails for any reason, she falls back to rule-based keyword matching over
  the same project knowledge, so she never goes silent — just less flexible
  about phrasing.

To turn on full LLM mode: get a key at
[console.anthropic.com](https://console.anthropic.com/), then
`export ANTHROPIC_API_KEY=sk-ant-...` before starting the backend (or put it
in `backend/.env` if you're using a tool that loads it, e.g. `python-dotenv`
or your shell's own `.env` support).

## One-Time Setup

Two ways to get running: natively (this section) or with Docker (skip
straight to §9, no local Python setup needed there).

1. Open the project root in your editor/terminal.
2. Create **one shared virtual environment**:

   ```bash
   python -m venv venvv
   ```

   Activate it — Windows: `venv\Scripts\activate` · macOS/Linux: `source venv/bin/activate`

3. Install dependencies for the backend and whichever frontend(s) you want
   — each has its own `requirements.txt`:

   ```bash
   pip install -r backend/requirements.txt
   pip install -r NiceGUI/requirements.txt     # only if you'll use NiceGUI
   pip install -r Streamlit/requirements.txt   # only if you'll use Streamlit
   ```

   The backend install downloads PyTorch, transformers, etc. — this can
   take a while, that's normal.

4. *(Optional, for Siara's full LLM mode)* Copy `backend/.env.example` to
   `backend/.env` and fill in your `ANTHROPIC_API_KEY`, or export it
   directly in your shell.

## Running the Project

You need **two terminals** (backend + one frontend), both with `venv` active.

**Terminal 1 — backend:**

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Wait for the console line `All models loaded: [...]` — the first run
downloads model weights, so it's slower; after that, startup is much faster.
Or run `run_backend.sh` / `run_backend.bat` from the project root.

**Terminal 2 — frontend (pick one):**

```bash
# NiceGUI (recommended, richer UI + Siara)
python NiceGUI/app.py

# — or — Streamlit (simpler, single page)
streamlit run Streamlit/app.py
```

Or the matching `run_frontend_nicegui.*` / `run_frontend_streamlit.*` script.

## Running with Docker

The whole project (backend + NiceGUI frontend) can run with a single
command, no local Python setup needed — everything else in this README
still applies if you'd rather run it natively.

**One-time:** *(optional)* copy `.env.example` to `.env` at the project
root and fill in `ANTHROPIC_API_KEY` for Siara's full LLM mode. `docker
compose` reads `.env` from the project root automatically. Skip this to run
Siara in rule-based fallback mode.

```bash
docker compose up --build
```

- Backend: `http://localhost:8000`
- NiceGUI frontend: `http://localhost:8080`

The first build/start is slow — the backend image downloads model weights
on first run, same as running natively. `docker-compose.yml` mounts a named
volume (`model-cache`) at the backend's `~/.cache`, so weights persist
across container restarts and rebuilds and won't re-download every time.

The NiceGUI container is given `BACKEND_URL=http://backend:8000` —
containers reach each other by **service name**, not `localhost`, since
they're on their own Docker network. If you're pointing a frontend
container at a backend running outside Docker instead, use
`http://host.docker.internal:8000` (Docker Desktop) rather than
`127.0.0.1`.

**Streamlit instead of/alongside NiceGUI** — it's defined but not started
by default, since NiceGUI is the primary frontend:

```bash
docker compose --profile streamlit up --build
```

**Individual services**, if you don't want to start everything:

```bash
docker compose up backend            # just the backend
docker compose up nicegui            # needs the backend already running/reachable
```

**Rebuilding after a code change:**

```bash
docker compose up --build            # rebuilds images that changed
```

**Stopping / cleaning up:**

```bash
docker compose down                  # stop and remove containers
docker compose down -v               # also remove the model-cache volume
```

## Testing

A pytest suite under `backend/tests/` covers both the pipeline's core logic
and the API endpoints — including Siara's `/api/assistant` in both LLM and
fallback modes.

```bash
cd backend
pip install pytest httpx   # already in requirements.txt
pytest tests -v
```

This runs in well under a second and **does not download or run any real
model weights** — `backend/tests/conftest.py` installs lightweight,
deterministic stand-ins for the heavy libraries (PyTorch, Ultralytics YOLO,
Faster-Whisper, Transformers, gTTS, langdetect) before anything imports
`pipeline.py`, and individual tests monkeypatch specific behavior (e.g. a
fake YOLO detection, a fake LLM reply) to check the actual Baseera logic —
direction math, template fallbacks, detection filtering, image decoding,
and every API endpoint's status codes and response shape.

What's covered:
- `_box_direction` for all 9 direction cases
- Detection filtering, sorting, and distance/direction math with fake YOLO output
- The Arabic-safety-net fallback in `generate_voice_response`
- Image decoding, including invalid-bytes handling
- Every `/api/find` path: happy path, missing image, missing audio *and*
  text, bad image bytes, pipeline exceptions
- `/api/assistant` in both LLM mode (mocked Claude client) and fallback mode

This is a *unit/integration* suite, not an end-to-end browser test — the
real webcam capture, microphone recording, and speech recognition/synthesis
are browser JavaScript and need to be checked by hand in an actual browser
(see §11 for what to check).

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Laptop gets very hot / fans spike / machine feels unresponsive while a request runs | This is the normal behavior of CPU inference libraries (PyTorch, Whisper) with no thread cap — by default they grab **every** CPU core/thread at once, which is exactly what makes a modest laptop feel like it's locked up. Set `BASEERA_CPU_THREADS` (in `backend/.env`, or the root `.env` if using Docker) to a lower number, e.g. `2`, and restart the backend — it'll be slower per request but the machine stays usable. `backend/pipeline.py` already defaults to half your CPU cores (min 1, max 4) even without setting anything, so this was already somewhat capped; lower it further if that's still too much for your hardware. This caps the AI models specifically — it doesn't change anything else about how the project runs. |
| "Backend not reachable" / connection failed | The FastAPI terminal isn't running, crashed while loading models, or `BACKEND_URL` doesn't match where it's actually running (default `http://127.0.0.1:8000`). |
| First request takes minutes | Normal on first run — model weights are downloading. Subsequent requests are much faster. |
| Mic button does nothing / recording never starts | The browser needs microphone permission — check the address bar for a blocked-permission icon. Recording requires a *secure context*: `localhost` is fine, but a plain `http://` address on another machine is not (use HTTPS or an SSH tunnel). |
| Webcam preview stays black | Same as above but for camera permission; also check no other app/tab is already using the camera. |
| `Could not decode the uploaded image` | The uploaded file isn't a valid image — re-upload or retake the photo. |
| Recorded voice question isn't understood | Recorded audio is `webm`/`opus` from the browser; Faster-Whisper decodes it via `ffmpeg` internally — make sure `ffmpeg` is installed and on your `PATH`. |
| Arabic response comes back in English | Deliberate safety net: if the LLM's Arabic generation doesn't actually contain Arabic characters, the backend falls back to a hand-written Arabic template instead of returning broken text. Not a bug. |
| Siara only gives short, keyword-y answers | She's running in fallback mode — set `ANTHROPIC_API_KEY` on the backend (see §6) for full conversational answers. |
| Distance numbers look off | `FOCAL_LENGTH` in `backend/pipeline.py` is a rough constant — recalibrate for your actual camera (measure a known object at a known distance and solve for focal length). |
| Dashboard shows "Not found" / no direction/distance right after a successful analysis | Make sure you're reading `matches[0]` for direction/distance — the backend nests those inside each match, it doesn't return top-level `direction`/`distance` fields, and the field is `query_text` not `transcribed_text`. An earlier prototype expected the wrong shape (and a different endpoint name, `/process`); `NiceGUI/pages/demo.py` matches the real `/api/find` contract. |
| Feedback form on the homepage silently does nothing | Fixed — it was posting to `/api/feedback`, which didn't exist on the backend. The backend now has that route (see §4) and logs submissions to `data/feedback_log.jsonl` at the project root. |
| Recording button said "captured successfully" but the backend never got any audio | Fixed — the previous JS called `emit_event('save_audio', ...)` to hand the recording to Python, but NiceGUI's real browser-side function is `emitEvent` (camelCase). The typo threw a silent `ReferenceError` in the browser console; the Python-side handler never fired, yet the on-screen "success" text was set unconditionally, so it looked like it worked. `NiceGUI/recording.py` replaces this with a Promise-based `ui.run_javascript()` call that returns the recorded audio directly — there's no separate event name to get wrong, and the UI only reports success after the data has actually arrived. |
| "Failed to connect to backend server" on Live Demo, even though the backend terminal shows it fully started | This used to lump two very different situations together — it's now split into two, and both were real bugs found while debugging this project, not hypotheticals: <br>**(a) It's actually just slow, not disconnected.** Check the backend terminal for `[transformers]` generation warnings right after you clicked the button — if they're there, the request *did* arrive and the backend was still processing when the frontend gave up waiting. On CPU-only hardware, Whisper + two YOLO models + the local LLM (called twice) + gTTS in one request can take well over a minute. `NiceGUI/pages/demo.py` now waits up to 3 minutes and reports this as a timeout, separately from a real connection failure. <br>**(b) The backend actually went down mid-session.** This shows as `httpx.ConnectError: All connection attempts failed`. Cause: `uvicorn --reload` watches the entire `backend/` folder, but the backend also *writes* files into that same folder while running — the downloaded YOLO weights (`yolov8n.pt`, `yolov8s.pt`) and, previously, `feedback_log.jsonl`. Each write triggers `--reload` to kill and fully restart the server (reloading every model, ~1 minute), and every request during that window fails to connect. Fixed two ways: `run_backend.sh`/`.bat` no longer pass `--reload` by default (this backend is too heavy to usefully auto-reload — restart it manually after code changes, or see the comment in those scripts for a `--reload-exclude` alternative), and the feedback log now writes to `data/feedback_log.jsonl` at the project root instead of inside `backend/`, so it can't trigger this even if `--reload` is re-enabled later. |
| Run history shows the photo but no bounding box | The backend is still running the old `pipeline.py`. Matches now carry a `bbox` field (see §4); restart the backend (or `docker compose up --build`) so it's picked up. Runs recorded before the restart stay without boxes. |
| Run history is empty after reloading the page | By design — history is kept in the browser tab's memory only, so photos and audio are never stored (see §1). |
| Header (logo/nav) never appears on the About or Live Demo pages | Fixed — the header used to fade in only after scrolling past a threshold tuned for the long Home page (`window.innerHeight * 0.45`), so shorter pages could be scrolled through entirely without ever crossing it. `NiceGUI/layout.py` now renders the header as always-visible on every page except Home, which keeps the original fade-in effect since it actually makes sense there. |

## Notes for Contributors

- **Models load once**, at backend startup — keep the backend terminal
  running while developing the frontend.
- `--reload` on uvicorn auto-restarts on backend code changes, which
  re-loads all models each time — drop it if that gets annoying while
  iterating on `pipeline.py`.
- To swap the local Qwen LLM for a cloud API, the two functions that call
  it are `extract_object_local()` and `generate_voice_response()` in
  `backend/pipeline.py`.
- CPU-only machines work but are noticeably slower for the LLM + YOLO +
  Whisper calls; PyTorch will pick up a CUDA GPU automatically if present.
- Keep `backend/assistant.py`'s `PROJECT_KNOWLEDGE` in sync with this
  README when either changes — that block of text *is* Siara's knowledge
  of the project.
- To deploy beyond your own machine, the backend and frontend can be
  pushed as two separate services and pointed at each other via
  `BACKEND_URL` — this is exactly what `docker-compose.yml` already does
  between containers (see §9).
- The Live Demo history needs `pillow` (listed in `NiceGUI/requirements.txt`)
  to draw the boxes. It relies on each match's `bbox` from `/api/find`, so
  if you change the match shape in `pipeline.py`, update `NiceGUI/history.py`
  too.
- New NiceGUI page: add `pages/your_page.py` with its own
  `@ui.page("/your-path")` function that calls `render_global_styles()`,
  `render_sticky_header(page="...")`, and `init_guide_bot()` at the top
  (same as `pages/about.py`), then import it in `app.py` — the import
  itself is what registers the route.
- Running under Docker and changed a Python file? `docker compose up
  --build` rebuilds only the images whose `Dockerfile`/context changed.
  Model weights persist across rebuilds via the `model-cache` volume, so a
  rebuild doesn't mean re-downloading them.


---

## 👥 Meet the Team

| Team Member | AI Focus Area | Deployment Focus Area | Contact |
| :--- | :--- | :--- | :--- |
| **Hager Ali** | Vision & Detection | Frontend (Streamlit & NiceGUI) | [![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white)](https://github.com/Hager-ali191) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/hager-ali-mohammed) |
| **Mariam Hazzaa** | Speech & Language | Backend API | [![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white)](https://github.com/mariamhazzaa) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mariam-hazzaa-2ab364389?utm_source=share_via&utm_content=profile&utm_medium=member_ios) |
| **Mariam Mohey** | Response & Voice | Containerization | [![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white)](https://github.com/MariamArafa-0) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mariam-arafa0) |
| **Menna Sobhe** | Orchestration & Testing | Cloud & Mobile Access | [![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white)](https://github.com/monyy77) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/menna-sobhe-03a2231ba) |

---
