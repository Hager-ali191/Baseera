#!/usr/bin/env bash
# Starts backend (localhost:8000, internal only) and NiceGUI (port 8080, public).
# NiceGUI comes up immediately; the backend takes a few minutes to load its
# models, and Live Demo requests work as soon as it finishes.

(cd backend && exec uvicorn main:app --host 127.0.0.1 --port 8000) &
(cd NiceGUI && exec python app.py) &

# If either process dies, exit so the platform restarts the whole container.
wait -n
exit 1
