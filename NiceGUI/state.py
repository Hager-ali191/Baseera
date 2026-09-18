class AppState:
    def __init__(self):
        self.image_bytes = None
        self.image_filename = "captured_scene.jpg"
        self.audio_bytes = None
        self.audio_filename = "recorded_voice.webm"

        # Backend cache — field names match backend/main.py's /api/find response exactly.
        self.transcribed_text = ""
        self.response_text = ""
        self.matches = []  # list of {object, direction, distance_m, confidence, model}
        self.direction = ""
        self.distance = ""
        self.confidence = 0.0


# One shared instance across all pages, matching the original single-file app's design
# (NiceGUI runs single-process, so this is per-server not per-visitor — fine for a demo;
# see README if you need real per-session isolation for multiple simultaneous users).
state = AppState()
