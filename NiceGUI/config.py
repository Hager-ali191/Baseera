import os

# Where the FastAPI backend lives. Override with an environment variable if
# the backend is running somewhere other than localhost (e.g. in Docker,
# this becomes the backend service's container name — see docker-compose.yml).
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Optional team photo shown on the Home page; falls back to initials if missing.
HAGER_PHOTO_PATH = "Baseera\\Team Photos\\Hager Ali.jpg"
MARIAMH_PHOTO_PATH = "Baseera\\Team Photos\\Mariam Hazzaa.jfif"
MARIAMM_PHOTO_PATH = "Baseera\\Team Photos\\Mariam Mohey.jpg"
MENNA_PHOTO_PATH = "Baseera\\Team Photos\\Menna Sobhe.jfif"
# Self-contained "image" for the robot avatar, built as an inline SVG data URI.
# NiceGUI's ui.chat_message(avatar=...) renders this as <img src="...">, so a
# raw emoji string ("🤖") gets requested as a URL path -> 404 in the console.
# A data URI avoids the network request entirely while still showing the emoji.
ROBOT_AVATAR = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40'>"
    "<rect width='40' height='40' rx='20' fill='%23FBBF24'/>"
    "<text x='50%' y='54%' font-size='22' text-anchor='middle' "
    "dominant-baseline='middle'>%F0%9F%A4%96</text></svg>"
)
