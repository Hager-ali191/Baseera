@echo off
cd backend
call ..\venv\Scripts\activate
REM No --reload: this backend loads Whisper + YOLO + a local LLM once at
REM startup (~1 minute), and it also writes files into this same folder
REM while running (downloaded model weights, feedback_log.jsonl). --reload
REM watches this whole folder for changes, so those writes were triggering
REM full automatic restarts mid-request -> every in-flight request failed
REM with a connection error. For active backend code editing, restart
REM manually, or use:
REM uvicorn main:app --reload --port 8000 --reload-exclude "*.pt" --reload-exclude "feedback_log.jsonl"
uvicorn main:app --port 8000
