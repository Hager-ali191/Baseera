#!/usr/bin/env bash
cd "$(dirname "$0")/backend"
source ../venv/bin/activate
# No --reload: this backend loads Whisper + YOLO + a local LLM once at
# startup (~1 minute), and it also writes files into this same folder while
# running (downloaded model weights, feedback_log.jsonl). --reload watches
# this whole folder for changes, so those writes were triggering full
# automatic restarts mid-request -> every in-flight request failed with a
# connection error. For active backend code editing, restart manually, or
# use: uvicorn main:app --reload --port 8000 --reload-exclude "*.pt" --reload-exclude "feedback_log.jsonl"
uvicorn main:app --port 8000
