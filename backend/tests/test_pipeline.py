"""
Unit tests for the core pipeline logic in backend/pipeline.py.

These run against the real cv2/numpy (cheap, deterministic) and against the
stubbed torch/YOLO/Whisper/LLM/gTTS/langdetect from conftest.py — so no real
model weights are downloaded or run, but the actual Baseera logic (direction
math, template fallbacks, detection filtering, image decoding) is exercised
for real.
"""

import io
import types

import numpy as np
import pytest
from PIL import Image

import pipeline as pl


# -----------------------------------------------------------------------------
# load_image_from_bytes
# -----------------------------------------------------------------------------
def _make_jpeg_bytes(width=100, height=80, color=(255, 0, 0)):
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_load_image_from_bytes_valid_image_decodes():
    frame = pl.load_image_from_bytes(_make_jpeg_bytes(120, 90))
    assert frame is not None
    assert frame.shape[0] == 90  # height
    assert frame.shape[1] == 120  # width


def test_load_image_from_bytes_invalid_bytes_raises():
    with pytest.raises(ValueError, match="Could not decode"):
        pl.load_image_from_bytes(b"this is not an image")


# -----------------------------------------------------------------------------
# guess_text_language
# -----------------------------------------------------------------------------
def test_guess_text_language_uses_langdetect(monkeypatch):
    monkeypatch.setattr(pl, "detect_text_language", lambda text: "ar")
    assert pl.guess_text_language("أين الهاتف؟") == "ar"


def test_guess_text_language_falls_back_on_unsupported_language(monkeypatch):
    monkeypatch.setattr(pl, "detect_text_language", lambda text: "fr")
    assert pl.guess_text_language("où est mon livre") == pl.DEFAULT_LANGUAGE


def test_guess_text_language_falls_back_on_exception(monkeypatch):
    def _boom(text):
        raise RuntimeError("langdetect blew up")

    monkeypatch.setattr(pl, "detect_text_language", _boom)
    assert pl.guess_text_language("??") == pl.DEFAULT_LANGUAGE


# -----------------------------------------------------------------------------
# _box_direction
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "cx,cy,expected",
    [
        (50, 40, "center"),        # dead center of a 100x80 frame
        (5, 40, "left"),
        (95, 40, "right"),
        (50, 5, "top"),
        (50, 75, "bottom"),
        (5, 5, "top-left"),
        (95, 5, "top-right"),
        (5, 75, "bottom-left"),
        (95, 75, "bottom-right"),
    ],
)
def test_box_direction(cx, cy, expected):
    assert pl._box_direction(cx, cy, frame_w=100, frame_h=80) == expected


# -----------------------------------------------------------------------------
# analyze_detections_multi_model
# -----------------------------------------------------------------------------
class _FakeBox:
    def __init__(self, cls_idx, conf, xyxy):
        self.cls = [cls_idx]
        self.conf = [conf]
        # Real YOLO boxes are tensors, so pipeline.py calls .tolist() on xyxy[0].
        self.xyxy = [np.array(xyxy)]


class _FakeYoloResult:
    def __init__(self, boxes):
        self.boxes = boxes


class _FakeYoloModel:
    """Stands in for a loaded YOLO model with a fixed set of detections."""

    def __init__(self, names, boxes):
        self.names = names
        self._boxes = boxes

    def __call__(self, frame, conf=0.3, verbose=False):
        return [_FakeYoloResult(self._boxes)]


def test_analyze_detections_matches_target_object(monkeypatch):
    # A 200x200 frame with one "laptop" box in the left half.
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    boxes = [
        _FakeBox(cls_idx=0, conf=0.9, xyxy=[10, 80, 60, 120]),  # laptop, width 50px
        _FakeBox(cls_idx=1, conf=0.8, xyxy=[150, 80, 180, 120]),  # chair, not requested
    ]
    fake_model = _FakeYoloModel(names={0: "laptop", 1: "chair"}, boxes=boxes)
    monkeypatch.setattr(pl, "detection_models", {"fake": fake_model})

    matches = pl.analyze_detections_multi_model(frame, "laptop", conf=0.3)

    assert len(matches) == 1
    match = matches[0]
    assert match["object"] == "laptop"
    assert match["confidence"] == 0.9
    assert match["direction"] == "left"
    assert match["distance_m"] > 0


def test_analyze_detections_no_matches_when_object_absent(monkeypatch):
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    boxes = [_FakeBox(cls_idx=0, conf=0.9, xyxy=[10, 80, 60, 120])]
    fake_model = _FakeYoloModel(names={0: "chair"}, boxes=boxes)
    monkeypatch.setattr(pl, "detection_models", {"fake": fake_model})

    matches = pl.analyze_detections_multi_model(frame, "laptop", conf=0.3)
    assert matches == []


def test_analyze_detections_sorted_by_confidence_descending(monkeypatch):
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    boxes = [
        _FakeBox(cls_idx=0, conf=0.4, xyxy=[10, 10, 40, 40]),
        _FakeBox(cls_idx=0, conf=0.95, xyxy=[60, 60, 90, 90]),
    ]
    fake_model = _FakeYoloModel(names={0: "cup"}, boxes=boxes)
    monkeypatch.setattr(pl, "detection_models", {"fake": fake_model})

    matches = pl.analyze_detections_multi_model(frame, "cup", conf=0.1)
    assert [m["confidence"] for m in matches] == [0.95, 0.4]


# -----------------------------------------------------------------------------
# _contains_arabic / _template_response
# -----------------------------------------------------------------------------
def test_contains_arabic_true_for_arabic_text():
    assert pl._contains_arabic("أين الهاتف") is True


def test_contains_arabic_false_for_english_text():
    assert pl._contains_arabic("where is the phone") is False


def test_template_response_english_with_match():
    match = {"direction": "left", "distance_m": 1.5}
    text = pl._template_response("laptop", match, "en")
    assert "laptop" in text
    assert "left" in text
    assert "1.5" in text


def test_template_response_english_without_match():
    text = pl._template_response("laptop", None, "en")
    assert "could not find" in text.lower()


def test_template_response_arabic_with_match():
    match = {"direction": "left", "distance_m": 1.5}
    text = pl._template_response("laptop", match, "ar")
    assert pl._contains_arabic(text)


# -----------------------------------------------------------------------------
# extract_object_local (LLM extraction step)
# -----------------------------------------------------------------------------
def test_extract_object_local_sanitizes_llm_output(monkeypatch):
    def _fake_llm(messages, max_new_tokens=10, do_sample=False, clean_up_tokenization_spaces=False):
        reply = {"role": "assistant", "content": "Cell Phone!! "}
        return [{"generated_text": list(messages) + [reply]}]

    monkeypatch.setattr(pl, "llm_pipeline", _fake_llm)
    assert pl.extract_object_local("where's my phone?") == "cell phone"


# -----------------------------------------------------------------------------
# generate_voice_response (with the Arabic-safety-net fallback)
# -----------------------------------------------------------------------------
def test_generate_voice_response_passthrough_when_valid(monkeypatch):
    def _fake_llm(messages, max_new_tokens=60):
        reply = {"role": "assistant", "content": "Yes, it's right there to your left."}
        return [{"generated_text": list(messages) + [reply]}]

    monkeypatch.setattr(pl, "llm_pipeline", _fake_llm)
    match = {"direction": "left", "distance_m": 1.0}
    text = pl.generate_voice_response("laptop", [match], language="en")
    assert text == "Yes, it's right there to your left."


def test_generate_voice_response_falls_back_when_arabic_requested_but_missing(monkeypatch):
    def _fake_llm(messages, max_new_tokens=60):
        # Model was asked for Arabic but (as sometimes happens) replied in English.
        reply = {"role": "assistant", "content": "Yes, found it to the left."}
        return [{"generated_text": list(messages) + [reply]}]

    monkeypatch.setattr(pl, "llm_pipeline", _fake_llm)
    match = {"direction": "left", "distance_m": 1.0}
    text = pl.generate_voice_response("laptop", [match], language="ar")
    assert pl._contains_arabic(text)  # template fallback kicked in


def test_generate_voice_response_falls_back_on_empty_output(monkeypatch):
    def _fake_llm(messages, max_new_tokens=60):
        reply = {"role": "assistant", "content": "   "}
        return [{"generated_text": list(messages) + [reply]}]

    monkeypatch.setattr(pl, "llm_pipeline", _fake_llm)
    text = pl.generate_voice_response("laptop", [], language="en")
    assert "could not find" in text.lower()


# -----------------------------------------------------------------------------
# speak (gTTS wrapper)
# -----------------------------------------------------------------------------
def test_speak_writes_a_file(tmp_path):
    out_path = tmp_path / "reply.mp3"
    result_path = pl.speak("hello there", language="en", filename=str(out_path))
    assert result_path == str(out_path)
    assert out_path.exists()
    assert out_path.stat().st_size > 0
