import httpx
from nicegui import ui

from config import BACKEND_URL


def feedback_section(backend_url: str = BACKEND_URL):
    """Renders the Feedback section and handles backend submission.

    Posts {name, email, message} as JSON to POST /api/feedback, which the
    backend persists to backend/feedback_log.jsonl (see backend/main.py).
    """
    with ui.card().classes(
        "w-full p-6 shadow-md rounded-xl bg-white-card border border-slate-200 gap-4"
    ):
        ui.label("Project Feedback & Experience").classes(
            "font-bold text-xl text-custom-dark"
        ).style("color: #1D2A78;")
        ui.label(
            "Have you tested Baseera? We would love to hear your thoughts and suggestions!"
        ).classes("text-xs text-slate-500 -mt-2")

        with ui.grid(columns=2).classes("w-full gap-4"):
            fb_name = ui.input("Your Name").props("outlined dense").classes("w-full")
            fb_email = ui.input("Your Email").props("outlined dense").classes("w-full")

        fb_message = ui.textarea("Feedback Message").props("outlined dense").classes("w-full")
        status_label = ui.label("").classes("text-xs italic h-4")

        async def submit_feedback():
            if not fb_message.value.strip():
                ui.notify("Please fill out the feedback message.", type="warning")
                return

            payload = {
                "name": fb_name.value.strip(),
                "email": fb_email.value.strip(),
                "message": fb_message.value.strip(),
            }

            status_label.set_text("Sending...")
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    res = await client.post(f"{backend_url}/api/feedback", json=payload)
                status_label.set_text("")
                if res.status_code == 200:
                    ui.notify("Thank you for your feedback!", type="positive")
                    fb_name.value = ""
                    fb_email.value = ""
                    fb_message.value = ""
                else:
                    try:
                        err = res.json().get("error", res.text)
                    except Exception:
                        err = res.text
                    ui.notify(f"Failed to submit feedback: {err}", type="negative")
            except Exception as ex:
                status_label.set_text("")
                ui.notify(f"Could not connect to backend server: {ex}", type="negative")

        ui.button("Submit Feedback", icon="send", on_click=submit_feedback).classes(
            "self-end px-6 py-2 rounded-lg cursor-pointer transition-transform hover:scale-105"
        ).style("background-color: #1D2A78; color: #FAD02C;")
