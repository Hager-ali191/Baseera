# Baseera backend — FastAPI + Whisper + YOLO + local LLM + gTTS
FROM python:3.11-slim

# ffmpeg: needed by Faster-Whisper/av to decode non-wav audio (e.g. the
# browser's recorded webm/opus). libgl1/libglib2.0-0: needed by OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# No --reload in production; model loading happens once at container start.
# First start downloads model weights — that's expected, not a hang.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
