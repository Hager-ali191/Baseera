# Single-container build: FastAPI backend + NiceGUI frontend in one image.
# Put this file at the PROJECT ROOT (next to backend/ and NiceGUI/).
# It is separate from docker-compose.yml, which keeps building the two
# services independently from backend/Dockerfile and NiceGUI/Dockerfile.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs containers as uid 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    BASEERA_CPU_THREADS=2 \
    BACKEND_URL=http://127.0.0.1:8000
WORKDIR /home/user/app

# Dependencies first, so code edits don't re-install PyTorch every build
COPY --chown=user backend/requirements.txt  backend-requirements.txt
COPY --chown=user NiceGUI/requirements.txt  nicegui-requirements.txt
RUN pip install --no-cache-dir -r backend-requirements.txt \
                               -r nicegui-requirements.txt pillow

COPY --chown=user . .
RUN mkdir -p data && chmod +x start_space.sh

EXPOSE 8080
CMD ["./start_space.sh"]
