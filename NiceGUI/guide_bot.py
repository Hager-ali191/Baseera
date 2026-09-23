# -*- coding: utf-8 -*-
"""
Siara — the floating guide bot with interactive, clickable option chips.
"""

import json
import httpx
from nicegui import ui
from config import BACKEND_URL, ROBOT_AVATAR

_SIARA_JS_INSTALLED = False

# Quick question options for the user to click
SUGGESTED_QUESTIONS = [
    "What is Baseera?",
    "How does it work?",
    "Which tech tools are used?",
    "Where is the Live Demo?",
    "How does YOLO work?",
    "How to use voice commands?",
]


def _install_siara_js():
    global _SIARA_JS_INSTALLED
    if _SIARA_JS_INSTALLED:
        return
    _SIARA_JS_INSTALLED = True

    ui.add_head_html("""
        <script>
        function siaraRecognizeSpeech() {
            return new Promise((resolve, reject) => {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    reject('Speech recognition is not supported in this browser. Try Chrome.');
                    return;
                }
                const recognition = new SpeechRecognition();
                recognition.lang = 'en-US';
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;
                recognition.onresult = (event) => resolve(event.results[0][0].transcript);
                recognition.onerror = (event) => reject(event.error || 'speech recognition error');
                recognition.start();
            });
        }
        function siaraSpeak(text) {
            if (!window.speechSynthesis) return;
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'en-US';
            utterance.rate = 1.0;
            window.speechSynthesis.speak(utterance);
        }
        </script>
    """)


async def _call_assistant(message: str, history: list) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/assistant",
                json={"message": message, "history": history},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"reply": f"I couldn't reach the backend just now ({e}). Is it running?", "source": "error"}


def init_guide_bot():
    _install_siara_js()

    conversation_history = []
    speak_replies = {"on": False}

    with ui.page_sticky(position="bottom-left", x_offset=24, y_offset=24).classes("z-50 flex flex-col items-start gap-2"):
        
        chat_card = ui.card().classes(
            "w-80 shadow-2xl rounded-2xl bg-white border border-yellow-200 p-3 z-50 flex flex-col justify-between"
        ).style("height: 490px; max-height: 490px; overflow: hidden;")
        chat_card.set_visibility(False)

        with chat_card:
            # Cleaned Header: Only "Siara" with mute & close controls
            with ui.row().classes("w-full items-center justify-between border-b pb-2 shrink-0"):
                ui.label("Siara").classes("font-bold text-gray-800 text-lg ml-1")
                with ui.row().classes("items-center gap-0"):
                    speak_btn = ui.button(icon="volume_off", on_click=lambda: toggle_speak()) \
                        .props("flat round dense size=sm").classes("text-gray-500") \
                        .tooltip("Read Siara's replies aloud")
                    ui.button(icon="close", on_click=lambda: chat_card.set_visibility(False)) \
                        .props("flat round dense size=sm").classes("text-gray-500")

            def toggle_speak():
                speak_replies["on"] = not speak_replies["on"]
                speak_btn.props(f"icon={'volume_up' if speak_replies['on'] else 'volume_off'}")

            # Chat Scroll Area
            chat_container = ui.scroll_area().classes("w-full my-1 text-sm flex-1").style("max-height: 340px;")
            
            status_label = ui.label("").classes("text-xs text-slate-400 italic shrink-0").style("min-height: 16px;")

            async def process_question(query: str):
                if not query:
                    return

                with chat_container:
                    ui.chat_message(query, sent=True)
                chat_container.scroll_to(percent=1.0)
                status_label.set_text("Siara is thinking...")

                result = await _call_assistant(query, conversation_history[-8:])
                reply = result.get("reply", "Sorry, something went wrong.")

                conversation_history.append({"role": "user", "content": query})
                conversation_history.append({"role": "assistant", "content": reply})

                with chat_container:
                    ui.chat_message(reply, sent=False, avatar=ROBOT_AVATAR)
                    
                    # Render new option buttons after every response
                    render_option_chips()

                chat_container.scroll_to(percent=1.0)
                status_label.set_text("")

                if speak_replies["on"]:
                    await ui.run_javascript(f"siaraSpeak({json.dumps(reply)})")

            def render_option_chips():
                """Renders clear, responsive option buttons under messages."""
                with ui.column().classes("w-full gap-1.5 my-2 shrink-0"):
                    ui.label("Or choose an option:").classes("text-xs text-gray-600 font-bold")
                    with ui.row().classes("w-full gap-1.5 flex-wrap"):
                        for q in SUGGESTED_QUESTIONS:
                            btn = ui.button(
                                q, 
                                on_click=lambda text=q: ui.timer(0, lambda: process_question(text), once=True)
                            )
                            btn.props("outline dense size=sm no-caps").classes(
                                "bg-yellow-50 text-yellow-950 border-yellow-400 rounded-lg hover:bg-yellow-200 px-3 py-1 font-semibold text-xs shadow-sm"
                            )

            # Initial Welcome Message & Options
            with chat_container:
                ui.chat_message(
                    "Hi! I'm Siara. Ask me anything about Baseera, or tap any option below to get instant answers:",
                    sent=False,
                    avatar=ROBOT_AVATAR,
                )
                render_option_chips()

            # Bottom Input Controls (Optional Typing & Mic)
            with ui.row().classes("w-full items-center gap-1 pt-2 border-t shrink-0 no-wrap").style("background: white;"):
                text_input = ui.input(placeholder="Type or click an option above...") \
                    .classes("flex-1 text-xs").props("dense outlined")

                async def handle_send():
                    q = text_input.value.strip()
                    text_input.value = ""
                    await process_question(q)

                async def handle_mic():
                    status_label.set_text("Listening...")
                    try:
                        transcript = await ui.run_javascript("return await siaraRecognizeSpeech()", timeout=15)
                    except Exception as e:
                        status_label.set_text("")
                        ui.notify(f"Voice input failed: {e}", type="negative")
                        return
                    status_label.set_text("")
                    await process_question(transcript)

                text_input.on("keydown.enter", handle_send)
                ui.button(icon="mic", on_click=handle_mic).props("flat dense round").classes("text-yellow-600") \
                    .tooltip("Ask by voice (English)")
                ui.button(icon="send", on_click=handle_send).props("flat dense round").classes("text-yellow-600")

        # Launcher Button
        ui.button(icon="smart_toy", on_click=lambda: chat_card.set_visibility(not chat_card.visible)) \
            .classes("bg-yellow-400 hover:bg-yellow-500 text-gray-900 shadow-xl rounded-full w-14 h-14 flex items-center justify-center") \
            .props("fab").tooltip("Ask Siara")