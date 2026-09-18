import os

from nicegui import ui

from config import HAGER_PHOTO_PATH
from feedback import feedback_section
from guide_bot import init_guide_bot
from layout import render_sticky_header
from styles import render_global_styles


@ui.page("/")
def home_page():
    render_global_styles()
    render_sticky_header(page="home")
    init_guide_bot()

    # HERO SECTION
    with ui.column().classes("hero-section w-full px-4 justify-center"):
        ui.html("""
            <div class="bg-shape shape-circle anim-1" style="top: 16% !important; left: 3%; width: 14px; height: 14px; border-width: 1.5px;"></div>
            <div class="bg-shape shape-square anim-2" style="top: 20% !important; left: 12%; width: 12px; height: 12px; border-width: 1.5px;"></div>
            <div class="bg-shape shape-ring anim-3" style="top: 15% !important; left: 25%; width: 18px; height: 18px; border-width: 1.5px;"></div>
            <div class="bg-shape shape-circle anim-1" style="top: 22% !important; left: 38%; width: 16px; height: 16px; border-width: 1.5px;"></div>
            <div class="bg-shape shape-square anim-2" style="top: 17% !important; left: 52%; width: 14px; height: 14px; border-width: 1.5px;"></div>
            <div class="bg-shape shape-ring anim-3" style="top: 24% !important; left: 66%; width: 20px; height: 20px; border-width: 1.5px;"></div>
            <div class="bg-shape shape-circle anim-1" style="top: 18% !important; right: 20%; width: 12px; height: 12px; border-width: 1.5px;"></div>
            <div class="bg-shape shape-square anim-3" style="top: 25% !important; right: 8%; width: 16px; height: 16px; border-width: 1.5px;"></div>
        """)

        with ui.column().classes("hero-content items-center text-center max-w-4xl mx-auto"):
            ui.label("BASEERA").classes(
                "fancy-title text-7xl md:text-8xl uppercase animate__animated animate__fadeInDown"
            )
            ui.label("AI-Powered Everyday Object Detection").classes(
                "text-2xl font-semibold mt-3 animate__animated animate__fadeInUp"
            ).style("color: #1D2A78;")
            ui.label(
                "An intelligent, voice-guided assistive platform empowering visually impaired "
                "individuals to effortlessly identify, locate, and interact with objects in "
                "real-time through multi-modal AI processing."
            ).classes(
                "max-w-3xl text-base font-medium mt-3 leading-relaxed opacity-95 animate__animated animate__fadeInUp"
            ).style("color: #1D2A78;")

            with ui.row().classes("gap-6 mt-8 animate__animated animate__fadeInUp"):
                ui.button(
                    "TRY LIVE DEMO", icon="rocket_launch", on_click=lambda: ui.navigate.to("/demo")
                ).classes(
                    "px-8 py-3.5 font-bold text-lg rounded-xl shadow-xl transition-transform hover:scale-105 pulse-glow cursor-pointer"
                ).style("background-color: #1D2A78; color: #FAD02C;")

                ui.button(
                    "VIEW GITHUB SOURCE",
                    icon="code",
                    on_click=lambda: ui.navigate.to(
                        "https://github.com/Hager-ali191/Baseera.git", new_tab=True
                    ),
                ).classes(
                    "px-8 py-3.5 font-bold text-lg rounded-xl shadow-xl transition-transform hover:scale-105 cursor-pointer"
                ).style("background-color: #1D2A78; color: #FAD02C;")

    # PIPELINE SECTION
    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-6 my-8").props("id=architecture"):
        ui.label("System Architecture & Pipeline").classes(
            "text-3xl font-bold text-center w-full text-custom-dark"
        ).style("color: #1D2A78;")
        ui.label(
            "How Baseera processes multi-modal queries seamlessly from speech to real-time "
            "object spatial analysis."
        ).classes("text-center text-slate-500 -mt-4 w-full")

        with ui.grid(columns=4).classes("w-full gap-4 mt-4"):
            pipeline_steps = [
                ("1. Voice & Vision Input", "mic",
                 "Captures audio prompt via HTML5 microphone and high-res scene images."),
                ("2. ASR & Vision Processing", "psychology",
                 "Converts speech to text (Whisper/ASR) & runs YOLO object detection models."),
                ("3. Spatial Logic Engine", "explore",
                 "Calculates bounding box positions, spatial direction (clock-wise), and distances."),
                ("4. Voice Response & Feedback", "volume_up",
                 "Generates contextual feedback and streams TTS audio back to user."),
            ]
            for title, icon, desc in pipeline_steps:
                with ui.card().classes(
                    "p-5 shadow-md rounded-xl bg-white-card border border-slate-200 items-center text-center gap-2 hover-up"
                ):
                    ui.icon(icon, size="lg").style("color: #1D2A78;")
                    ui.label(title).classes("font-bold text-base mt-2 text-custom-dark").style("color: #1D2A78;")
                    ui.label(desc).classes("text-xs text-slate-500")

    # NTI GRADUATION BANNER
    with ui.column().classes("w-full max-w-6xl mx-auto px-8 my-4"):
        with ui.card().classes(
            "w-full p-6 shadow-md rounded-xl text-center items-center hover-up pulse-glow"
        ).style("background-color: #1D2A78; border: 2px solid #FAD02C;"):
            ui.label("Graduation Project").classes("text-xl font-bold").style("color: #FAD02C;")
            ui.label("National Telecommunication Institute (NTI) Training Program").classes(
                "text-sm text-slate-200 mt-1"
            )

    # TEAM SECTION
    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-6 my-4").props("id=team"):
        ui.label("Meet the Engineers").classes(
            "text-3xl font-bold text-center w-full text-custom-dark"
        ).style("color: #1D2A78;")

        with ui.grid(columns=2).classes("w-full gap-8 mt-2"):
            team_members = [
                ("Hager Ali", "Computer Vision & Frontend Engineer",
                 "Responsible for Computer Vision object detection pipelines, real-time image "
                 "processing, and designing interactive UIs using Streamlit & NiceGUI.",
                 ["Vision Models", "NiceGUI", "Streamlit"],
                 "https://www.linkedin.com/in/hager-ali-460316365", "alihager191@gmail.com", "HA", True),
                ("Mariam Hazzaa", "Speech, NLP & Backend API Engineer",
                 "Architected Speech-to-Text pipelines, NLP text understanding modules, and "
                 "implemented robust RESTful backend APIs for system integration.",
                 ["ASR / Speech", "FastAPI", "NLP"],
                 "#", "mariamhazzaa@gmail.com", "MH", False),
                ("Mariam Mohey", "Audio Processing & DevOps Engineer",
                 "Engineered Text-to-Speech audio response generation, managed Docker "
                 "containerization, and established multi-service environment workflows.",
                 ["TTS Audio", "Docker", "Containerization"],
                 "#", "mariammohey@gmail.com", "MM", False),
                ("Menna Sobhe", "System Orchestration & QA Lead",
                 "Supervised system orchestration, end-to-end integration testing, mobile "
                 "access configuration, and cloud service deployments.",
                 ["Orchestration", "Testing", "Cloud Deployment"],
                 "#", "mennasobhe@gmail.com", "MS", False),
            ]
            for name, role, desc, skills, linkedin, email, initials, has_photo in team_members:
                with ui.card().classes(
                    "p-8 shadow-md rounded-2xl bg-white-card border border-slate-200 gap-6 hover-up"
                ):
                    with ui.row().classes("items-center gap-6"):
                        if has_photo and os.path.exists(HAGER_PHOTO_PATH):
                            ui.image(HAGER_PHOTO_PATH).classes(
                                "w-24 h-24 rounded-full object-cover shadow-lg border-2 border-amber-300"
                            )
                        else:
                            ui.avatar(initials, color="primary", text_color="white").classes(
                                "w-24 h-24 text-2xl font-bold shadow-lg border-2 border-amber-300"
                            )
                        with ui.column().classes("gap-1"):
                            ui.label(name).classes("text-2xl font-bold text-custom-dark").style("color: #1D2A78;")
                            ui.label(role).classes("text-xs font-semibold text-slate-500")

                    ui.label(desc).classes("text-xs text-slate-600 leading-relaxed")

                    with ui.row().classes("gap-2"):
                        for skill in skills:
                            ui.label(skill).classes("skill-chip")

                    with ui.row().classes("gap-4 mt-2 items-center"):
                        ui.html(
                            f'<a href="{linkedin}" target="_blank" style="color: #2563eb; font-size: 1.25rem;">'
                            f'<i class="fa-brands fa-linkedin"></i></a>'
                        )
                        ui.html(
                            f'<a href="mailto:{email}" style="color: #ef4444; font-size: 1.25rem;">'
                            f'<i class="fa-solid fa-envelope"></i></a>'
                        )

    # SPECIAL THANKS
    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-4 my-2"):
        ui.label("Special Thanks & Mentorship").classes(
            "text-3xl font-bold text-center w-full text-custom-dark mb-2"
        ).style("color: #1D2A78;")

        with ui.grid(columns=2).classes("w-full gap-6"):
            for name, blurb, linkedin_url in [
                ("Eng. Mohamed Yossri",
                 "We extend our heartfelt gratitude for his invaluable guidance, continuous "
                 "technical mentorship, and unwavering support throughout the development of Baseera.",
                 "https://www.linkedin.com/in/mohamed-yossri"),
                ("Eng. Abdelaziz Fadel",
                 "Special thanks for his technical insights, inspiring mentorship, and dedication "
                 "in guiding our team toward technical excellence.",
                 "https://www.linkedin.com/in/abdelaziz-fadel"),
            ]:
                with ui.card().classes(
                    "w-full p-6 shadow-lg rounded-2xl bg-white-card border-2 border-amber-300 items-center text-center gap-3 hover-up"
                ):
                    ui.icon("star", size="lg").style("color: #FAD02C;")
                    ui.label(name).classes("text-xl font-black text-custom-dark").style("color: #1D2A78;")
                    ui.label(blurb).classes("text-xs text-slate-600 leading-relaxed")
                    ui.button(
                        "LinkedIn Profile",
                        icon="open_in_new",
                        on_click=lambda url=linkedin_url: ui.navigate.to(url, new_tab=True),
                    ).classes(
                        "mt-2 px-5 py-2 text-xs font-bold rounded-xl shadow-md cursor-pointer transition-transform hover:scale-105"
                    ).style("background-color: #1D2A78; color: #FAD02C;")

    # FEEDBACK SECTION
    with ui.column().classes("w-full max-w-4xl mx-auto p-8 gap-4 my-4"):
        feedback_section()
