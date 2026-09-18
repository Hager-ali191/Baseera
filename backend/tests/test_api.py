"""
Tests for the FastAPI endpoints in backend/main.py: /health, /api/find, and
/api/assistant. The heavy pipeline internals are monkeypatched so these run
fast and don't need real model weights (that's what test_pipeline.py is for).
"""

import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import main as backend_main


@pytest.fixture()
def client():
    return TestClient(backend_main.app)


def _jpeg_bytes():
    img = Image.new("RGB", (64, 48), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# -----------------------------------------------------------------------------
# /health
# -----------------------------------------------------------------------------
def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "models" in body


# -----------------------------------------------------------------------------
# /api/find
# -----------------------------------------------------------------------------
def test_find_requires_image(client):
    resp = client.post("/api/find", data={"text": "where is my laptop"})
    # FastAPI's own validation: `image` is a required file field.
    assert resp.status_code == 422


def test_find_requires_audio_or_text(client):
    resp = client.post(
        "/api/find",
        files={"image": ("scene.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "Send either" in resp.json()["error"]


def test_find_rejects_bad_image_bytes(client):
    resp = client.post(
        "/api/find",
        files={"image": ("scene.jpg", b"not an image", "image/jpeg")},
        data={"text": "where is my laptop"},
    )
    assert resp.status_code == 400
    assert "Could not decode" in resp.json()["error"]


def test_find_happy_path(client, monkeypatch):
    fake_result = {
        "query_text": "where is my laptop",
        "language": "en",
        "target_object": "laptop",
        "matches": [
            {"object": "laptop", "direction": "left", "distance_m": 1.2, "confidence": 0.9, "model": "yolov8n"}
        ],
        "reply_text": "Yes, I found your laptop to the left, about 1.2 meters away.",
    }
    monkeypatch.setattr(backend_main.pipeline, "run_full_pipeline", lambda **kwargs: dict(fake_result))

    resp = client.post(
        "/api/find",
        files={"image": ("scene.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"text": "where is my laptop"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["query_text"] == "where is my laptop"
    assert body["target_object"] == "laptop"
    assert body["matches"][0]["direction"] == "left"
    # audio_base64 should be present and decode to the stub mp3 bytes from conftest's gTTS stub.
    assert base64.b64decode(body["audio_base64"]) == b"ID3-stub-mp3-bytes"


def test_find_reports_pipeline_failure_as_500(client, monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(backend_main.pipeline, "run_full_pipeline", _boom)

    resp = client.post(
        "/api/find",
        files={"image": ("scene.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"text": "where is my laptop"},
    )
    assert resp.status_code == 500
    assert "Pipeline failed" in resp.json()["error"]


# -----------------------------------------------------------------------------
# /api/assistant (Siara)
# -----------------------------------------------------------------------------
def test_assistant_rejects_empty_message(client):
    resp = client.post("/api/assistant", json={"message": "   "})
    assert resp.status_code == 400


def test_assistant_uses_fallback_without_api_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = client.post("/api/assistant", json={"message": "what tech stack is this built with?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    assert "FastAPI" in body["reply"]


def test_assistant_uses_llm_when_available(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-tests")

    class _FakeTextBlock:
        type = "text"
        text = "Baseera helps visually impaired users find objects using voice and a camera."

    class _FakeResponse:
        content = [_FakeTextBlock()]

    class _FakeMessages:
        def create(self, **kwargs):
            return _FakeResponse()

    class _FakeAnthropicClient:
        def __init__(self, api_key=None):
            self.messages = _FakeMessages()

    import sys
    import types

    fake_anthropic_module = types.ModuleType("anthropic")
    fake_anthropic_module.Anthropic = _FakeAnthropicClient
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic_module)

    resp = client.post("/api/assistant", json={"message": "what is Baseera for?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "llm"
    assert "visually impaired" in body["reply"]


def test_assistant_falls_back_if_llm_call_raises(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-tests")

    class _BoomClient:
        def __init__(self, api_key=None):
            raise RuntimeError("network unreachable")

    import sys
    import types

    fake_anthropic_module = types.ModuleType("anthropic")
    fake_anthropic_module.Anthropic = _BoomClient
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic_module)

    resp = client.post("/api/assistant", json={"message": "what tech stack is this?"})
    assert resp.status_code == 200
    assert resp.json()["source"] == "fallback"


# -----------------------------------------------------------------------------
# /api/feedback
# -----------------------------------------------------------------------------
def test_feedback_rejects_empty_message(client):
    resp = client.post("/api/feedback", json={"name": "A", "email": "a@example.com", "message": "   "})
    assert resp.status_code == 400


def test_feedback_accepts_and_persists(client, tmp_path, monkeypatch):
    log_path = tmp_path / "feedback_log.jsonl"
    monkeypatch.setattr(backend_main, "FEEDBACK_LOG_PATH", str(log_path))

    resp = client.post(
        "/api/feedback",
        json={"name": "Sara", "email": "sara@example.com", "message": "Loved the demo!"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert log_path.exists()
    saved = log_path.read_text(encoding="utf-8").strip()
    assert "Loved the demo!" in saved
    assert "sara@example.com" in saved
