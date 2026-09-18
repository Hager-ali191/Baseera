"""
Real microphone recording and webcam capture for the Live Demo page.

WHY THIS REPLACES THE OLD APPROACH
The previous implementation used `mediaRecorder.onstop` to base64-encode the
recording and call a JS function named `emit_event('save_audio', ...)` to
send it to Python. That function doesn't exist in NiceGUI — the real
browser-side API is `emitEvent` (camelCase). Calling an undefined function
throws a ReferenceError, which fails *silently* in the browser console; the
Python-side `ui.on("save_audio", ...)` handler never fires, so the audio is
never actually captured — even though the on-screen status text ("Voice
captured and processed successfully!") was set unconditionally, regardless
of whether that call actually succeeded, which made the bug easy to miss.

This version avoids the whole custom-event mechanism: `ui.run_javascript()`
can await a JS Promise and return its resolved value directly back into
Python in the same call, so there's no separate event name to get wrong and
no way for the UI to report success before the data has actually arrived.
"""

import base64

from nicegui import ui

_MEDIA_JS_INSTALLED = False


def install_media_js():
    """Installs the recording/webcam JS helpers once per page."""
    global _MEDIA_JS_INSTALLED
    if _MEDIA_JS_INSTALLED:
        return
    _MEDIA_JS_INSTALLED = True
    ui.add_head_html("""
        <script>
        // ---- real microphone recording (MediaRecorder) ----
        let baseeraRecorder = null;
        let baseeraChunks = [];

        async function baseeraStartRecording() {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            baseeraChunks = [];
            baseeraRecorder = new MediaRecorder(stream);
            baseeraRecorder.ondataavailable = (e) => { if (e.data.size > 0) baseeraChunks.push(e.data); };
            baseeraRecorder.start();
        }

        function baseeraStopRecording() {
            return new Promise((resolve, reject) => {
                if (!baseeraRecorder) { reject('Not currently recording.'); return; }
                baseeraRecorder.onstop = () => {
                    const blob = new Blob(baseeraChunks, { type: 'audio/webm' });
                    baseeraRecorder.stream.getTracks().forEach(t => t.stop());
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);   // data: URL, base64-encoded
                    reader.onerror = () => reject('Could not read recorded audio.');
                    reader.readAsDataURL(blob);
                };
                baseeraRecorder.stop();
            });
        }

        // ---- live webcam preview + frame capture ----
        function baseeraInitWebcam() {
            const video = document.getElementById('webcam-feed');
            if (!video || video.srcObject) return;
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => { video.srcObject = stream; })
                .catch(err => console.error('Baseera webcam error:', err));
        }
        function baseeraCaptureFrame() {
            const video = document.getElementById('webcam-feed');
            if (!video || !video.videoWidth) return null;
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            return canvas.toDataURL('image/jpeg', 0.9);
        }
        function baseeraStopWebcam() {
            const video = document.getElementById('webcam-feed');
            if (video && video.srcObject) {
                video.srcObject.getTracks().forEach(t => t.stop());
                video.srcObject = null;
            }
        }
        </script>
    """)


def decode_data_url(data_url: str) -> bytes:
    """'data:audio/webm;base64,AAAA...' -> raw bytes."""
    _header, encoded = data_url.split(",", 1)
    return base64.b64decode(encoded)