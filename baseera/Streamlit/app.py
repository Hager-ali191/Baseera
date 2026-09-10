"""
Baseera Streamlit frontend.

Run with:
    streamlit run app.py

(run this from inside the `frontend/` folder, with your venv active,
 and make sure the FastAPI backend is already running on port 8000)
"""

import base64
import os

import requests
import streamlit as st

API_URL = os.environ.get("BASEERA_API_URL", "http://localhost:8000")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")

st.set_page_config(page_title="Baseera", page_icon="🧭", layout="centered")

if os.path.exists(LOGO_PATH):
    col_logo, col_title = st.columns([1, 3])
    with col_logo:
        st.image(LOGO_PATH, width=120)
    with col_title:
        st.title("Baseera")
        st.caption("Voice-Guided Object Finder")
else:
    st.title("Baseera — Voice-Guided Object Finder")

st.write("Ask where an object is (by typing or by voice), show it a photo of the room, and Baseera will tell you where it is.")

# --- backend health check -------------------------------------------------
with st.sidebar:
    st.subheader("Backend status")
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        if r.ok:
            st.success("Connected to backend ✅")
        else:
            st.error("Backend reachable but unhealthy")
    except Exception:
        st.error("Backend not reachable — start it with `uvicorn main:app` from the backend/ folder.")

# --- question input ---------------------------------------------------
st.subheader("1. Ask your question")
input_mode = st.radio(
    "How do you want to ask?",
    ["Type it", "Upload a voice recording", "Record audio directly"],
    horizontal=True
)
query_text = None
audio_file = None

# if input_mode == "Type it":
#     query_text = st.text_input("Your question", placeholder="Where is my laptop? / أين الهاتف؟")
# elif input_mode == "Upload a voice recording":
#     audio_file = st.file_uploader("Upload a voice question", type=["wav", "mp3", "m4a"])
if input_mode == "Record audio directly":
    audio_file = st.audio_input("Record your voice question")

# --- image input --------------------------------------------------------
st.subheader("2. Show it the room")
image_mode = st.radio("Image source", ["Upload a photo", "Use my camera"], horizontal=True)

if image_mode == "Upload a photo":
    image_file = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])
else:
    image_file = st.camera_input("Take a photo")

conf = st.slider("Detection confidence threshold", 0.1, 0.9, 0.3, 0.05)

# --- run -------------------------------------------------------------
st.subheader("3. Find it")
if st.button("🔍 Find it", type="primary"):
    if image_file is None:
        st.error("Please provide a photo of the room.")
    elif not query_text and audio_file is None:
        st.error("Please type a question or upload a voice recording.")
    else:
        with st.spinner("Looking around..."):
            files = {
                "image": (
                    getattr(image_file, "name", "photo.jpg"),
                    image_file.getvalue(),
                    "image/jpeg",
                )
            }
            data = {"conf": str(conf)}

            if audio_file is not None:
                files["audio"] = (
                    getattr(audio_file, "name", "recorded_audio.wav"),
                    audio_file.read(),
                    "audio/wav"
                )
            else:
                data["text"] = query_text

            try:
                resp = requests.post(f"{API_URL}/api/find", files=files, data=data, timeout=1000)
                resp.raise_for_status()
                result = resp.json()
            except Exception as e:
                st.error(f"Request failed: {e}")
                result = None

        if result and "error" not in result:
            st.success("Done!")
            st.markdown(f"**Heard:** {result['query_text']}")
            st.markdown(f"**Detected language:** {result['language']}")
            st.markdown(f"**Looking for:** {result['target_object']}")
            st.markdown(f"**Response:** {result['reply_text']}")

            if result["matches"]:
                st.markdown("**All matches (best first):**")
                st.table(result["matches"])
            else:
                st.info("No matching object was detected in the photo.")

            audio_bytes = base64.b64decode(result["audio_base64"])
            st.audio(audio_bytes, format="audio/mp3")
        elif result:
            st.error(result.get("error", "Something went wrong."))
