"""Run history for the Live Demo page.

Each finished /api/find call is recorded with add_entry(); history_panel()
renders the list. Per run it shows the time, question, language, target class,
the photo with a labelled bounding box on every match, a table of
confidence / direction / distance / model / box coordinates, the spoken reply
(with replay) and the response time.

Privacy: history lives in memory for this browser tab only (app.storage.client).
Nothing is written to disk, which keeps the README promise that photos and
voice are never stored. Reloading the page clears it.
"""
from __future__ import annotations

import base64
import io
from datetime import datetime

from nicegui import app, ui
from PIL import Image, ImageDraw, ImageFont, ImageOps

MAX_ENTRIES = 20          # oldest runs are dropped beyond this
PREVIEW_MAX_WIDTH = 900   # annotated preview is downscaled to keep memory small
BOX_COLORS = ["#22c55e", "#FAD02C", "#3b82f6", "#ef4444", "#a855f7"]
NAVY = "#1D2A78"


# ---------------------------------------------------------------- helpers
def _store() -> list[dict]:
    return app.storage.client.setdefault("history", [])


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def annotate(image_bytes: bytes, matches: list[dict]) -> str | None:
    """Return a data-URI JPEG of the photo with a labelled box per match.

    Matches without a "bbox" are skipped, so this is safe against an
    un-updated backend.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # OpenCV (used by the backend) applies EXIF rotation when decoding,
        # Pillow does not. Apply it here so box coordinates line up on
        # phone photos.
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception:
        return None

    scale = min(1.0, PREVIEW_MAX_WIDTH / img.width)
    if scale < 1.0:
        img = img.resize((round(img.width * scale), round(img.height * scale)))

    draw = ImageDraw.Draw(img)
    font = _font(max(14, img.width // 45))
    stroke = max(2, img.width // 250)

    for i, m in enumerate(matches):
        bbox = m.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        color = BOX_COLORS[i % len(BOX_COLORS)]
        x1, y1, x2, y2 = (v * scale for v in bbox)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=stroke)

        label = f'{m.get("object", "?")} {round(m.get("confidence", 0) * 100)}%'
        l, t, r, b = draw.textbbox((0, 0), label, font=font)
        tw, th = r - l, b - t
        ly = max(0, y1 - th - 10)
        draw.rectangle([x1, ly, x1 + tw + 12, ly + th + 10], fill=color)
        draw.text((x1 + 6, ly + 4 - t), label, fill=NAVY, font=font)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- public API
def add_entry(*, image_bytes: bytes, response: dict, elapsed_s: float) -> None:
    """Record one finished /api/find run. `response` is the backend JSON as-is."""
    matches = response.get("matches") or []
    audio_b64 = response.get("audio_base64")
    history = _store()
    history.insert(0, {
        "run": (history[0]["run"] + 1) if history else 1,
        "time": datetime.now(),
        "query": response.get("query_text", ""),
        "language": response.get("language", "?"),
        "target": response.get("target_object") or "unknown",
        "matches": matches,
        "reply": response.get("reply_text", ""),
        "audio_src": f"data:audio/mp3;base64,{audio_b64}" if audio_b64 else None,
        "image": annotate(image_bytes, matches),
        "elapsed_s": elapsed_s,
    })
    del history[MAX_ENTRIES:]          # newest first, drop the oldest


def clear_history() -> None:
    _store().clear()
    history_panel.refresh()


def _matches_table(matches: list[dict]) -> None:
    columns = [
        {"name": n, "label": label, "field": n, "align": "left"}
        for n, label in [
            ("object", "Object"), ("confidence", "Confidence"),
            ("direction", "Direction"), ("distance", "Distance"),
            ("model", "Model"), ("box", "Box (x1, y1, x2, y2 px)"),
        ]
    ]
    rows = [
        {
            "id": i,
            "object": m.get("object", ""),
            "confidence": f'{int(m.get("confidence", 0) * 100)}%',
            "direction": m.get("direction", ""),
            "distance": f'{m["distance_m"]} m' if "distance_m" in m else "",
            "model": m.get("model", ""),
            "box": "[" + ", ".join(str(v) for v in m["bbox"]) + "]" if m.get("bbox") else "n/a",
        }
        for i, m in enumerate(matches)
    ]
    ui.table(columns=columns, rows=rows, row_key="id").props("flat dense").classes("w-full")


@ui.refreshable
def history_panel() -> None:
    history = _store()

    with ui.row().classes("w-full items-center justify-between"):
        ui.label(f"Run History ({len(history)})").classes("font-bold text-lg").style(f"color: {NAVY};")
        if history:
            ui.button("Clear history", icon="delete_outline", on_click=clear_history).props(
                "flat dense no-caps"
            ).style(f"color: {NAVY};")

    if not history:
        ui.label(
            "No runs yet. Run a search above and every run will be listed here."
        ).classes("text-sm text-slate-500")
        return

    ui.label(
        "Kept in this browser tab only. Photos and audio are never saved to disk."
    ).classes("text-xs text-slate-500")

    for n, e in enumerate(history):
        found = bool(e["matches"])
        title = (
            f'Run {e["run"]}  |  {e["time"].strftime("%H:%M:%S")}  |  '
            f'{e["target"]}  |  {len(e["matches"])} found' if found else
            f'Run {e["run"]}  |  {e["time"].strftime("%H:%M:%S")}  |  '
            f'{e["target"]}  |  not found'
        )
        with ui.expansion(
            title, icon="check_circle" if found else "search_off", value=(n == 0)
        ).classes("w-full border border-slate-200 rounded-xl").props(
            f'header-class="text-weight-bold" expand-icon-class="text-grey-7"'
        ):
            with ui.row().classes("w-full gap-6 p-3 items-start").style("flex-wrap: wrap;"):
                if e["image"]:
                    ui.image(e["image"]).classes("rounded-xl").style(
                        f"flex: 1 1 320px; min-width: 260px; max-width: 520px; border: 2px solid {NAVY};"
                    )

                with ui.column().classes("gap-2").style("flex: 1 1 280px; min-width: 0;"):
                    ui.label(f'Question: {e["query"] or "(none)"}').props("dir=auto").classes("text-sm font-semibold")
                    with ui.row().classes("gap-2"):
                        ui.chip(f'Language: {e["language"]}').props("dense color=grey-7 text-color=white")
                        ui.chip(f'Target: {e["target"]}').props("dense color=primary text-color=white")
                        ui.chip(f'Took {e["elapsed_s"]:.1f} s').props("dense color=grey-4 text-color=black")
                    ui.label(f'Assistant response: {e["reply"]}').props("dir=auto").classes("text-sm")
                    if e["audio_src"]:
                        ui.audio(e["audio_src"]).props("controls").classes("w-full")

            with ui.column().classes("w-full px-3 pb-3"):
                if found:
                    _matches_table(e["matches"])
                else:
                    ui.label("The target class was not detected in this photo.").classes(
                        "text-sm text-slate-500"
                    )
