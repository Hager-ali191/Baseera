from nicegui import ui

from guide_bot import init_guide_bot
from layout import render_sticky_header
from styles import render_global_styles


@ui.page("/about")
def about_page():
    render_global_styles()
    render_sticky_header(page="about")
    init_guide_bot()

    with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-6").style("margin-top: 70px;"):
        with ui.card().classes(
            "w-full p-6 shadow-md rounded-2xl text-center items-center"
        ).style("background-color: #1D2A78; border: 2px solid #FAD02C;"):
            ui.label("About Baseera").classes("text-2xl font-extrabold").style("color: #FAD02C;")
            ui.label('"Baseera" means insight — helping people see what a camera sees.').classes(
                "text-sm font-medium text-slate-200 mt-1"
            )

        with ui.card().classes("w-full p-6 shadow-md rounded-xl bg-white-card border border-slate-200 gap-3"):
            ui.label("Our Mission").classes("font-bold text-lg").style("color: #1D2A78;")
            ui.label(
                "Baseera is an assistive-technology project built to help visually impaired "
                "users locate everyday objects around them independently. Instead of asking "
                "someone else 'where did I put my keys?', a user can simply ask Baseera out "
                "loud, point a camera at the room, and get a spoken answer with direction and "
                "distance."
            ).classes("text-sm text-slate-700 leading-relaxed")

        with ui.card().classes("w-full p-6 shadow-md rounded-xl bg-white-card border border-slate-200 gap-3"):
            ui.label("Who It's For").classes("font-bold text-lg").style("color: #1D2A78;")
            ui.label(
                "Primarily built for blind and low-vision users, but useful for anyone in a "
                "low-visibility situation. Baseera understands questions in both English and "
                "Arabic."
            ).classes("text-sm text-slate-700 leading-relaxed")

        with ui.card().classes("w-full p-6 shadow-md rounded-xl bg-white-card border border-slate-200 gap-3"):
            ui.label("What It Can Do").classes("font-bold text-lg").style("color: #1D2A78;")
            with ui.column().classes("gap-2 w-full"):
                for icon, text in [
                    ("record_voice_over", "Understand a spoken or typed question in English or Arabic"),
                    ("visibility", "Detect everyday objects in a photo (laptop, phone, keys, and more)"),
                    ("explore", "Estimate which direction the object is in and roughly how far away"),
                    ("volume_up", "Speak the answer back in a natural sentence"),
                    ("smart_toy", "Guide you around the site itself through Siara, the built-in assistant"),
                ]:
                    with ui.row().classes("items-center gap-3"):
                        ui.icon(icon).style("color: #1D2A78;")
                        ui.label(text).classes("text-sm text-slate-700")

        with ui.card().classes("w-full p-6 shadow-md rounded-xl bg-white-card border border-slate-200 gap-2"):
            ui.label("Frequently Asked Questions").classes("font-bold text-lg mb-2").style("color: #1D2A78;")
            faqs = [
                ("Do I need an internet connection?",
                 "The core object-finding pipeline runs fully on the machine hosting the backend, "
                 "so no internet is needed once it's set up. Siara's full conversational mode does "
                 "call out to an LLM API, but she still works offline in a simpler rule-based mode."),
                ("What languages are supported for finding objects?",
                 "English and Arabic today — ask in either language and Baseera replies in the "
                 "same one."),
                ("Does it work with any camera?",
                 "Yes, any webcam or uploaded photo. Distance estimates use a rough calibration "
                 "constant that may need tuning for a specific camera."),
                ("Is my voice or photo stored anywhere?",
                 "No — everything is processed in memory for a single request and discarded "
                 "immediately after the response is returned."),
            ]
            for question, answer in faqs:
                with ui.expansion(question).classes("w-full text-sm font-semibold"):
                    ui.label(answer).classes("text-sm text-slate-600 leading-relaxed p-2")
