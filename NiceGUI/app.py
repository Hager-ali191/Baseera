"""
Baseera — NiceGUI frontend entry point.

Each page now lives in its own file under pages/ (Home, About, Live Demo).
Importing a page module registers its @ui.page(...) route as a side effect
— that's the only reason these imports are here and seemingly "unused".
"""

from nicegui import ui

from pages import about, demo, home  # noqa: F401  (side effect: registers routes)

# ui.run(title="Baseera - Vision & Voice Assistant", port=8080, reload=False)
ui.run(
    title="Baseera - Vision & Voice Assistant",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8080)),
    storage_secret="your_unique_secret_key",
    reload=False
)
