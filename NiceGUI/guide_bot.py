# -*- coding: utf-8 -*-
"""
Siara — the floating guide bot, present on every page (Home, About, Demo).
"""

import json
import httpx
from nicegui import ui
from config import BACKEND_URL, ROBOT_AVATAR

_SIARA_JS_INSTALLED = False


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

    # Floating container pinned at bottom-left
    with ui.page_sticky(position="bottom-left", x_offset=24, y_offset=24).classes("z-50 flex flex-col items-start gap-2"):
        
        # Chat Card with strict height and flex-col layout
        chat_card = ui.card().classes(
            "w-80 shadow-2xl rounded-2xl bg-white border border-yellow-200 flex flex-col justify-between p-3 z-50 overflow-hidden"
        ).style("height: 440px;")
        chat_card.set_visibility(False)

        with chat_card:
            # Header
            with ui.row().classes("w-full items-center justify-between border-b pb-2 flex-shrink-0"):
                with ui.row().classes("items-center gap-2"):
                    ui.avatar(ROBOT_AVATAR, size="sm") if ROBOT_AVATAR else ui.avatar(icon="smart_toy", color="yellow-500", text_color="white").classes("w-8 h-8 text-sm")
                    ui.label("Siara (Guide Bot)").classes("font-bold text-gray-800 text-sm")
                with ui.row().classes("items-center gap-0"):
                    speak_btn = ui.button(icon="volume_off", on_click=lambda: toggle_speak()) \
                        .props("flat round dense size=sm").classes("text-gray-500") \
                        .tooltip("Read Siara's replies aloud")
                    ui.button(icon="close", on_click=lambda: chat_card.set_visibility(False)) \
                        .props("flat round dense size=sm").classes("text-gray-500")

            def toggle_speak():
                speak_replies["on"] = not speak_replies["on"]
                speak_btn.props(f"icon={'volume_up' if speak_replies['on'] else 'volume_off'}")

            # Fixed scroll area height so it leaves space for the input row
            chat_container = ui.scroll_area().classes("w-full pr-2 text-sm").style("height: 280px;")
            with chat_container:
                ui.chat_message(
                    "Hi! I'm Siara. Ask me anything about how Baseera works, how to use "
                    "this site, or if you can't find something — type below or press the mic.",
                    sent=False,
                    avatar=ROBOT_AVATAR,
                )

            status_label = ui.label("").classes("text-xs text-slate-400 italic h-4 flex-shrink-0")

            # Input Controls Area at Bottom
            with ui.column().classes("w-full gap-1 pt-2 border-t flex-shrink-0"):
                with ui.row().classes("w-full items-center gap-1 no-wrap"):
                    text_input = ui.input(placeholder="Ask Siara a question...") \
                        .classes("flex-grow text-xs").props("dense outlined")

                    async def handle_send():
                        query = text_input.value.strip()
                        if not query:
                            return

                        with chat_container:
                            ui.chat_message(query, sent=True)
                        text_input.value = ""
                        chat_container.scroll_to(percent=1.0)
                        status_label.set_text("Siara is thinking...")

                        result = await _call_assistant(query, conversation_history[-8:])
                        reply = result.get("reply", "Sorry, something went wrong.")

                        conversation_history.append({"role": "user", "content": query})
                        conversation_history.append({"role": "assistant", "content": reply})

                        with chat_container:
                            ui.chat_message(reply, sent=False, avatar=ROBOT_AVATAR)
                        chat_container.scroll_to(percent=1.0)
                        status_label.set_text("")

                        if speak_replies["on"]:
                            await ui.run_javascript(f"siaraSpeak({json.dumps(reply)})")

                    async def handle_mic():
                        status_label.set_text("Listening...")
                        try:
                            transcript = await ui.run_javascript("return await siaraRecognizeSpeech()", timeout=15)
                        except Exception as e:
                            status_label.set_text("")
                            ui.notify(f"Voice input failed: {e}", type="negative")
                            return
                        status_label.set_text("")
                        text_input.value = transcript
                        await handle_send()

                    text_input.on("keydown.enter", handle_send)
                    ui.button(icon="mic", on_click=handle_mic).props("flat dense round").classes("text-yellow-600") \
                        .tooltip("Ask by voice (English)")
                    ui.button(icon="send", on_click=handle_send).props("flat dense round").classes("text-yellow-600")

        # Floating launcher button
        ui.button(icon="smart_toy", on_click=lambda: chat_card.set_visibility(not chat_card.visible)) \
            .classes("bg-yellow-400 hover:bg-yellow-500 text-gray-900 shadow-xl rounded-full w-14 h-14 flex items-center justify-center") \
            .props("fab").tooltip("Ask Siara")