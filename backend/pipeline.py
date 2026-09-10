import re

import cv2
import numpy as np
import torch
from gtts import gTTS
from ultralytics import YOLO
from faster_whisper import WhisperModel
from transformers import pipeline
from langdetect import detect as detect_text_language


FOCAL_LENGTH = 600  # recalibrate for actual camera

KNOWN_WIDTHS_CM = {
    "laptop": 35, "cell phone": 7, "person": 50, "chair": 50,
    "bottle": 7, "cup": 9, "book": 20, "keyboard": 45,
    "mouse": 12, "tv": 120, "backpack": 30, "handbag": 25,
    "remote": 5, "umbrella": 100, "couch": 180,
    "default": 30,
}

SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "gtts_code": "en"},
    "ar": {"name": "Arabic", "gtts_code": "ar"},
}
DEFAULT_LANGUAGE = "en"

OBJECT_NAME_AR = {
    "laptop": "الحاسوب المحمول", "cell phone": "الهاتف", "person": "شخص",
    "chair": "الكرسي", "bottle": "الزجاجة", "cup": "الكوب", "book": "الكتاب",
    "keyboard": "لوحة المفاتيح", "mouse": "الفأرة", "tv": "التلفاز",
    "backpack": "حقيبة الظهر", "handbag": "الحقيبة", "remote": "جهاز التحكم",
    "umbrella": "المظلة", "couch": "الأريكة",
}
DIRECTION_AR = {
    "left": "اليسار", "right": "اليمين", "center": "الأمام مباشرة",
    "top": "الأعلى", "bottom": "الأسفل",
    "top-left": "أعلى اليسار", "top-right": "أعلى اليمين",
    "bottom-left": "أسفل اليسار", "bottom-right": "أسفل اليمين",
}

DETECTION_MODEL_NAMES = {
    "yolov8n": "yolov8n.pt",
    "yolov8s": "yolov8s.pt",
}

_ARABIC_CHAR_RE = re.compile(r"[\u0600-\u06FF]")


print("[Baseera] Loading Whisper (speech-to-text)...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

print("[Baseera] Loading YOLO detection models...")
detection_models = {name: YOLO(path) for name, path in DETECTION_MODEL_NAMES.items()}

print("[Baseera] Loading local instruct LLM (Qwen2.5-1.5B-Instruct)...")
device_id = 0 if torch.cuda.is_available() else -1
llm_pipeline = pipeline(
    "text-generation",
    model="Qwen/Qwen2.5-1.5B-Instruct",
    dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device=device_id,
)

print("[Baseera] All models loaded:", list(detection_models.keys()))



def load_image_from_bytes(image_bytes: bytes):
    """Decodes raw uploaded image bytes into a BGR numpy frame (what OpenCV/YOLO expect)."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode the uploaded image.")
    return frame


def guess_text_language(text: str) -> str:
    """Best-effort language guess for a typed (non-audio) query."""
    try:
        lang = detect_text_language(text)
    except Exception:
        return DEFAULT_LANGUAGE
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def extract_object_local(query_text: str) -> str:
    """Returns a single lowercase English object name extracted from the query."""
    messages = [
        {"role": "system", "content": (
            "You are an information extraction system. The user is asking about a missing object, "
            "in English or Arabic. Identify the object and return ONLY its name as a single lowercase "
            "English word or short phrase from common object vocabulary (e.g. laptop, cell phone, "
            "backpack, bottle, cup, book, chair, tv, remote, keyboard, mouse, umbrella, couch). "
            "Return only the object name in English, nothing else -- no translation notes, no punctuation."
        )},
        {"role": "user", "content": query_text},
    ]
    
    outputs = llm_pipeline(
        messages, 
        max_new_tokens=10,
        do_sample=False,
        clean_up_tokenization_spaces=False
    )
    
    result = outputs[0]["generated_text"][-1]["content"].strip().lower()
    return re.sub(r"[^a-z0-9 ]", "", result)





def _box_direction(cx, cy, frame_w, frame_h):
    frame_cx, frame_cy = frame_w // 2, frame_h // 2
    h_dir = "left" if cx < frame_cx - (frame_w * 0.2) else "right" if cx > frame_cx + (frame_w * 0.2) else "center"
    v_dir = "top" if cy < frame_cy - (frame_h * 0.2) else "bottom" if cy > frame_cy + (frame_h * 0.2) else "middle"
    if h_dir != "center" and v_dir != "middle":
        return f"{v_dir}-{h_dir}"
    return h_dir if v_dir == "middle" else v_dir


def analyze_detections_multi_model(frame, target_object: str, conf: float = 0.3):
    h, w = frame.shape[:2]
    all_matches = []

    for model_name, model in detection_models.items():
        results = model(frame, conf=conf, verbose=False)[0]
        for box in results.boxes:
            class_name = model.names[int(box.cls[0])].lower()
            confidence = float(box.conf[0])

            if target_object not in class_name and class_name not in target_object:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            pixel_width = x2 - x1
            cx, cy = x1 + pixel_width // 2, y1 + (y2 - y1) // 2

            real_w_cm = KNOWN_WIDTHS_CM.get(class_name, KNOWN_WIDTHS_CM["default"])
            dist_cm = (real_w_cm * FOCAL_LENGTH) / pixel_width if pixel_width > 0 else 0

            all_matches.append({
                "object": class_name,
                "direction": _box_direction(cx, cy, w, h),
                "distance_m": round(dist_cm / 100, 2),
                "confidence": round(confidence, 2),
                "model": model_name,
            })

    all_matches.sort(key=lambda m: m["confidence"], reverse=True)
    return all_matches







def _contains_arabic(text: str) -> bool:
    return bool(_ARABIC_CHAR_RE.search(text))


def _template_response(target_object, best_match, language):
    """Guaranteed-correct fallback using hand-written bilingual templates."""
    if language == "ar":
        object_ar = OBJECT_NAME_AR.get(target_object, target_object)
        if best_match:
            direction_ar = DIRECTION_AR.get(best_match["direction"], best_match["direction"])
            return (f"نعم، وجدت {object_ar}. إنه في جهة {direction_ar}، "
                    f"على بعد حوالي {best_match['distance_m']} متر.")
        return f"بحثت حولي، لكن لم أتمكن من العثور على {object_ar} في مجال الرؤية."

    if best_match:
        return (f"Yes, I found your {target_object}. It is located to the {best_match['direction']}, "
                f"about {best_match['distance_m']} meters away.")
    return f"I looked around, but I could not find your {target_object} in the camera view."


def generate_voice_response(target_object, matches, language=DEFAULT_LANGUAGE):
    best_match = matches[0] if matches else None
    language_name = SUPPORTED_LANGUAGES.get(language, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])["name"]

    facts = (
        f"Object: {target_object}. "
        + (f"Found: yes. Direction: {best_match['direction']}. Distance: {best_match['distance_m']} meters."
           if best_match else "Found: no.")
    )

    messages = [
        {"role": "system", "content": (
            f"You are a voice assistant for a blind user. Given the facts below, write ONE short, "
            f"natural spoken sentence in {language_name} describing whether the object was found and, "
            f"if so, where. Respond ONLY in {language_name}, nothing else."
        )},
        {"role": "user", "content": facts},
    ]
    outputs = llm_pipeline(messages, max_new_tokens=60)
    generated = outputs[0]["generated_text"][-1]["content"].strip()

    if language == "ar" and not _contains_arabic(generated):
        return _template_response(target_object, best_match, language)
    if not generated:
        return _template_response(target_object, best_match, language)
    return generated


def speak(text: str, language: str = DEFAULT_LANGUAGE, filename: str = "response.mp3") -> str:
    """Synthesizes speech and saves it to `filename`. Returns the path."""
    gtts_code = SUPPORTED_LANGUAGES.get(language, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])["gtts_code"]
    tts = gTTS(text=text, lang=gtts_code)
    tts.save(filename)
    return filename


def run_full_pipeline(frame, audio_bytes: bytes | None, query_text: str | None, conf: float = 0.3) -> dict:
    """
    One call = the whole notebook flow, minus Colab-specific capture.
    Give it EITHER audio_bytes OR query_text, plus an already-decoded frame.
    """
    import tempfile
    import os

    if audio_bytes is not None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            segments, info = whisper_model.transcribe(tmp_path)
            query_text = "".join(segment.text for segment in segments).strip()
            language = info.language if info.language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        finally:
            os.remove(tmp_path)
    elif query_text is not None:
        language = guess_text_language(query_text)
    else:
        raise ValueError("Provide either audio_bytes or query_text.")

    target_object = extract_object_local(query_text)
    matches = analyze_detections_multi_model(frame, target_object, conf=conf)
    reply_text = generate_voice_response(target_object, matches, language=language)

    return {
        "query_text": query_text,
        "language": language,
        "target_object": target_object,
        "matches": matches,
        "reply_text": reply_text,
    }
