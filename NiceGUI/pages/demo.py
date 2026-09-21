import base64
import time

import httpx
from nicegui import ui

from config import BACKEND_URL
from guide_bot import init_guide_bot
from history import add_entry, history_panel
from layout import render_sticky_header
from recording import decode_data_url, install_media_js
from state import state
from styles import render_global_styles


@ui.page("/demo")
def demo_page():
    render_global_styles()
    render_sticky_header(page="demo")
    init_guide_bot()
    install_media_js()

    with (
        ui.column()
        .classes("w-full max-w-5xl mx-auto p-6 gap-6 items-center animate__animated animate__fadeIn")
        .style("margin-top: 70px;")
    ):
        with ui.card().classes(
            "w-full p-4 shadow-sm rounded-xl text-center items-center"
        ).style("background-color: #1D2A78; border: 2px solid #FAD02C;"):
            ui.label("Live Interactive Workspace").classes("text-2xl font-black").style("color: #FAD02C;")
            ui.label(
                "Record voice prompt, capture/upload scene frame, and run AI inference pipeline."
            ).classes("text-xs font-semibold text-slate-200 mt-1")

        # -------------------------------------------------------------------
        # 1. VOICE SECTION — real microphone recording (see recording.py for
        #    why this replaces the old emit_event-based version, which never
        #    actually delivered the audio to Python).
        # -------------------------------------------------------------------
        with ui.card().classes(
            "w-full p-6 shadow-md rounded-xl bg-white-card border border-slate-200 gap-4 hover-up"
        ):
            ui.label("1. Voice Command Input").classes("font-bold text-lg text-custom-dark").style("color: #1D2A78;")

            with ui.row().classes("w-full gap-6 items-stretch"):
                with ui.column().classes(
                    "items-center justify-center p-6 rounded-2xl border-2 border-slate-300"
                ).style("flex: 7 1 0%; min-width: 0; background: rgba(29, 42, 120, 0.03);"):
                    record_btn = ui.button(
                        "🎙️ START VOICE RECORDING", on_click=lambda: toggle_recording()
                    ).classes(
                        "font-black rounded-2xl w-full max-w-md"
                    ).style(
                        "background-color: #1D2A78; color: #FAD02C; padding: 18px 36px; "
                        "font-size: 18px; box-shadow: 0 8px 20px rgba(29, 42, 120, 0.25);"
                    )
                    rec_status = ui.label("Click the button above to speak your command...").classes(
                        "text-xs font-semibold mt-3 opacity-85"
                    )
                    rec_playback = ui.column().classes("w-full items-center mt-2")

                    is_recording = {"value": False}

                    async def toggle_recording():
                        if not is_recording["value"]:
                            try:
                                await ui.run_javascript("await baseeraStartRecording()", timeout=100)
                            except Exception as e:
                                ui.notify(f"Could not access microphone: {e}", type="negative")
                                rec_status.set_text("Microphone access denied or not supported.")
                                return
                            is_recording["value"] = True
                            rec_playback.clear()
                            record_btn.set_text("⏹️ STOP RECORDING")
                            record_btn.classes(add="recording-active")
                            rec_status.set_text("Recording in progress... Speak clearly!")
                        else:
                            try:
                                data_url = await ui.run_javascript("return await baseeraStopRecording()", timeout=30)
                            except Exception as e:
                                ui.notify(f"Recording failed: {e}", type="negative")
                                rec_status.set_text("Recording failed — please try again.")
                                is_recording["value"] = False
                                record_btn.set_text("🎙️ START VOICE RECORDING")
                                record_btn.classes(remove="recording-active")
                                return
                            state.audio_bytes = decode_data_url(data_url)
                            state.audio_filename = "recorded_voice.webm"
                            is_recording["value"] = False
                            record_btn.set_text("🎙️ START VOICE RECORDING")
                            record_btn.classes(remove="recording-active")
                            rec_status.set_text("Voice captured! Listen back below, or record again to redo it.")
                            ui.notify("Recording captured!", type="positive")
                            # data_url is already a full "data:audio/webm;base64,..." string
                            # from the browser — play it back directly so the person can
                            # confirm what was actually recorded before running the pipeline.
                            with rec_playback:
                                ui.audio(data_url).props("controls").classes("w-full max-w-md")

                with ui.column().classes("justify-center w-full").style("flex: 5 1 0%; min-width: 0;"):
                    ui.label("Or Upload Pre-Recorded Audio").classes("text-xs font-semibold text-slate-500 mb-2")

                    def handle_audio_upload(e):
                        content = e.content.read()
                        state.audio_bytes = content
                        state.audio_filename = e.name
                        ui.notify("Audio query uploaded successfully!", type="positive")

                        ext = e.name.rsplit(".", 1)[-1].lower() if "." in e.name else ""
                        mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "webm": "audio/webm",
                                "m4a": "audio/mp4", "ogg": "audio/ogg"}.get(ext, "audio/mpeg")
                        data_url = f"data:{mime};base64,{base64.b64encode(content).decode()}"
                        rec_playback.clear()
                        with rec_playback:
                            ui.audio(data_url).props("controls").classes("w-full max-w-md")

                    ui.upload(
                        label="Upload Audio File (.wav, .mp3)", on_upload=handle_audio_upload, max_files=1
                    ).props('accept="audio/*"').classes("w-full cursor-pointer")

                    ui.label("...or just type it instead").classes("text-xs font-semibold text-slate-500 mt-4 mb-2")
                    text_query_input = ui.input(placeholder="e.g. Where is my laptop?").classes("w-full").props("outlined dense")

        # -------------------------------------------------------------------
        # 2. CAMERA SECTION
        # -------------------------------------------------------------------
        with ui.card().classes(
            "w-full p-6 shadow-md rounded-xl bg-white-card border border-slate-200 gap-4 hover-up"
        ):
            ui.label("2. Camera & Image Input").classes("font-bold text-lg text-custom-dark").style("color: #1D2A78;")

            with ui.row().classes("w-full gap-6 items-start"):
                with ui.column().classes("items-center").style("flex: 7 1 0%; min-width: 0;"):
                    cam_label = ui.label("Live Web Camera Stream").classes("text-xs font-semibold text-slate-500 mb-2")
                    video_el = ui.html(
                        '<video id="webcam-feed" autoplay playsinline style="width: 100%; '
                        'min-height: 320px; max-height: 480px; border-radius: 14px; background: #000; '
                        'border: 2px solid #1D2A78; object-fit: cover;"></video>'
                    )
                    captured_image = ui.image().classes(
                        "w-full rounded-2xl border-2"
                    ).style("min-height: 320px; max-height: 480px; object-fit: cover; border-color: #1D2A78; display: none;")
                    ui.timer(0.5, lambda: ui.run_javascript("baseeraInitWebcam()"), once=True)

                    async def capture_frame():
                        data_url = await ui.run_javascript("return baseeraCaptureFrame()")
                        if data_url:
                            state.image_bytes = decode_data_url(data_url)
                            state.image_filename = "webcam_capture.jpg"
                            # Release the camera and swap the live preview for the still
                            # photo just taken, so it's clear exactly what will be sent.
                            await ui.run_javascript("baseeraStopWebcam()")
                            captured_image.set_source(data_url)
                            captured_image.style("display: block;")
                            video_el.set_visibility(False)
                            cam_label.set_text("Photo Captured")
                            snap_btn.set_visibility(False)
                            retake_btn.set_visibility(True)
                            ui.notify("Camera frame captured!", type="positive")
                        else:
                            ui.notify("Webcam not ready yet — allow camera access and try again.", type="warning")

                    async def retake_photo():
                        captured_image.style("display: none;")
                        video_el.set_visibility(True)
                        cam_label.set_text("Live Web Camera Stream")
                        await ui.run_javascript("baseeraInitWebcam()")
                        snap_btn.set_visibility(True)
                        retake_btn.set_visibility(False)

                    with ui.row().classes("mt-4 gap-3"):
                        snap_btn = ui.button("Snap Camera Frame", icon="photo_camera", on_click=capture_frame).classes(
                            "px-6 py-2.5 text-xs font-bold rounded-xl cursor-pointer"
                        ).style("background-color: #1D2A78; color: #FAD02C;")
                        retake_btn = ui.button("Retake Photo", icon="replay", on_click=retake_photo).classes(
                            "px-6 py-2.5 text-xs font-bold rounded-xl cursor-pointer"
                        ).style("background-color: #FAD02C; color: #1D2A78;")
                        retake_btn.set_visibility(False)

                with ui.column().classes("w-full").style("flex: 5 1 0%; min-width: 0;"):
                    ui.label("Or Upload Image File").classes("text-xs font-semibold text-slate-500 mb-2")

                    def handle_image_upload(e):
                        state.image_bytes = e.content.read()
                        state.image_filename = e.name
                        ui.notify("Image uploaded successfully!", type="positive")

                    ui.upload(
                        label="Upload Scene Image", on_upload=handle_image_upload, max_files=1
                    ).props('accept="image/*"').classes("w-full cursor-pointer")

        # -------------------------------------------------------------------
        # 3. RESULTS & RUN PIPELINE
        # -------------------------------------------------------------------
        with ui.column().classes("w-full items-center my-4"):
            result_container = ui.column().classes("w-full gap-4")

            progress_row = ui.row().classes("w-full items-center justify-center gap-3").style("display: none;")
            with progress_row:
                ui.spinner(size="lg", color="amber-8")
                progress_label = ui.label("").classes("text-sm font-semibold").style("color: #1D2A78;")

            elapsed = {"seconds": 0}

            def _tick():
                elapsed["seconds"] += 1
                m, s = divmod(elapsed["seconds"], 60)
                progress_label.set_text(
                    f"⏳ Still processing... {m}:{s:02d} elapsed. Whisper + YOLO + the local "
                    f"LLM + text-to-speech are all running on CPU in one request — this "
                    f"routinely takes several minutes, especially on the first request. "
                    f"Keep this tab open."
                )

            progress_timer = ui.timer(1.0, _tick, active=False)

            async def run_pipeline():
                if not state.image_bytes:
                    ui.notify("Please capture or upload an image frame first.", type="warning")
                    return
                if not state.audio_bytes and not text_query_input.value.strip():
                    ui.notify("Please record/upload audio, or type your question.", type="warning")
                    return

                result_container.clear()
                run_btn.disable()
                elapsed["seconds"] = 0
                progress_label.set_text("⏳ Starting... sending your photo and question to the backend.")
                progress_row.style("display: flex;")
                progress_timer.active = True

                # Snapshot the photo being sent, so the history shows exactly this
                # image even if the user retakes/uploads another while waiting.
                sent_image_bytes = state.image_bytes
                started_at = time.perf_counter()

                files = {"image": (state.image_filename, sent_image_bytes, "image/jpeg")}
                data_fields = {}
                if state.audio_bytes:
                    files["audio"] = (state.audio_filename, state.audio_bytes, "audio/webm")
                else:
                    data_fields["text"] = text_query_input.value.strip()

                try:
                    # Very generous timeout: on CPU-only hardware, Whisper + two YOLO
                    # models + the local LLM (called twice) + gTTS in a single request
                    # can genuinely take many minutes — this was raised from 180s after
                    # real runs kept exceeding that on modest hardware. The elapsed-time
                    # indicator above is what actually tells the person whether it's
                    # still working, not this number — this is just "don't give up too
                    # early".
                    async with httpx.AsyncClient(timeout=1800) as client:
                        res = await client.post(f"{BACKEND_URL}/api/find", files=files, data=data_fields)

                    if res.status_code == 200:
                        data = res.json()
                        # Field names match backend/main.py's /api/find response exactly —
                        # it's "query_text", not "transcribed_text", and direction/distance
                        # live inside each entry of "matches", not as top-level fields.
                        state.transcribed_text = data.get("query_text", "")
                        state.response_text = data.get("reply_text", "")
                        state.matches = data.get("matches", [])
                        best_match = state.matches[0] if state.matches else None
                        state.direction = best_match["direction"] if best_match else ""
                        state.distance = f"{best_match['distance_m']} m" if best_match else ""
                        state.confidence = best_match["confidence"] if best_match else 0.0

                        add_entry(
                            image_bytes=sent_image_bytes,
                            response=data,
                            elapsed_s=time.perf_counter() - started_at,
                        )
                        history_panel.refresh()

                        with result_container:
                            with ui.card().classes(
                                "w-full p-6 shadow-xl rounded-xl bg-white-card border-2 border-emerald-500 gap-4 animate__animated animate__fadeInUp"
                            ):
                                ui.label("AI Dashboard Results").classes("text-xl font-bold text-emerald-600")

                                if state.transcribed_text:
                                    ui.label(f"Transcribed Audio: '{state.transcribed_text}'").classes(
                                        "text-sm font-semibold italic"
                                    )

                                ui.label(f"Assistant Response: {state.response_text}").classes("text-base font-medium")

                                with ui.row().classes("gap-4 mt-2"):
                                    if state.direction:
                                        ui.chip(f"Direction: {state.direction}").props("color=primary text-color=white")
                                    if state.distance:
                                        ui.chip(f"Distance: {state.distance}").props("color=secondary text-color=black")
                                    if best_match:
                                        ui.chip(f"Confidence: {int(state.confidence * 100)}%").props(
                                            "color=grey-7 text-color=white"
                                        )

                                if len(state.matches) > 1:
                                    ui.label(f"All matches ({len(state.matches)}):").classes(
                                        "text-xs font-bold text-slate-400 uppercase tracking-wider mt-2"
                                    )
                                    for m in state.matches:
                                        ui.label(
                                            f"• {m['object']} — {m['direction']}, {m['distance_m']} m ({int(m['confidence']*100)}%)"
                                        ).classes("text-xs text-slate-600")

                                if data.get("audio_base64"):
                                    audio_src = f"data:audio/mp3;base64,{data['audio_base64']}"
                                    ui.audio(audio_src).props("autoplay controls")
                    else:
                        try:
                            err = res.json().get("error", res.text)
                        except Exception:
                            err = res.text
                        ui.notify(f"Backend error: {err}", type="negative")
                except httpx.TimeoutException:
                    ui.notify(
                        f"The backend still hadn't responded after {elapsed['seconds']//60} "
                        f"minutes, so the frontend gave up waiting. This usually means "
                        f"something is genuinely stuck (check the backend terminal for an "
                        f"error), not just slow — normal CPU-only requests should finish "
                        f"well before this. Wait for the backend log to settle, then try "
                        f"again.",
                        type="negative",
                    )
                except httpx.ConnectError as ex:
                    ui.notify(
                        f"Could not reach the backend at {BACKEND_URL} at all: {ex}. "
                        f"Make sure it's running and BACKEND_URL is correct.",
                        type="negative",
                    )
                except Exception as ex:
                    ui.notify(f"Request to the backend failed: {ex}", type="negative")
                finally:
                    progress_timer.active = False
                    progress_row.style("display: none;")
                    run_btn.enable()

            run_btn = ui.button("SEE DASHBOARD RESULTS", icon="dashboard", on_click=run_pipeline).classes(
                "px-10 py-4 text-xl font-black rounded-2xl shadow-2xl pulse-glow transition-transform hover:scale-105 cursor-pointer"
            ).style("background-color: #1D2A78; color: #FAD02C;")

        # -------------------------------------------------------------------
        # 4. RUN HISTORY — every run this session, with the annotated photo
        #    and the full detection details.
        # -------------------------------------------------------------------
        with ui.card().classes(
            "w-full p-6 shadow-md rounded-xl bg-white-card border border-slate-200 gap-3"
        ):
            history_panel()
