"""
Shared test setup.

backend/pipeline.py loads Whisper, YOLO and a local LLM at IMPORT time
(module-level code), which is exactly right for production (load once,
serve many requests) but wrong for unit tests: we don't want every test run
to download gigabytes of model weights and spend minutes loading them.

So before anything imports `pipeline` or `main`, this file installs light,
fully-deterministic fake modules in `sys.modules` for every heavy dependency
(torch, ultralytics, faster_whisper, transformers, gTTS, langdetect).
Real, lightweight dependencies that are cheap and deterministic (cv2, numpy)
are left alone and used for real.

Individual tests then monkeypatch specific pieces of `pipeline` (e.g.
`pipeline.detection_models`, `pipeline.llm_pipeline`) to control behavior
for that test, rather than relying on these generic stubs.
"""

import os
import sys
import types

import pytest

# backend/main.py and backend/pipeline.py use bare `import pipeline` style
# imports (they're designed to be run from inside `backend/`). Add that
# directory to sys.path so the same bare imports work from the test suite,
# wherever pytest is invoked from.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def _install_stub_modules():
    # ---- torch --------------------------------------------------------
    if "torch" not in sys.modules:
        torch_stub = types.ModuleType("torch")
        torch_stub.float16 = "float16"
        torch_stub.float32 = "float32"

        class _Cuda:
            @staticmethod
            def is_available():
                return False

        torch_stub.cuda = _Cuda()
        sys.modules["torch"] = torch_stub

    # ---- ultralytics (YOLO) --------------------------------------------
    if "ultralytics" not in sys.modules:
        ultralytics_stub = types.ModuleType("ultralytics")

        class _StubYOLO:
            """No-op stand-in; real detection is monkeypatched per-test."""

            def __init__(self, path):
                self.path = path
                self.names = {}

            def __call__(self, frame, conf=0.3, verbose=False):
                return [types.SimpleNamespace(boxes=[])]

        ultralytics_stub.YOLO = _StubYOLO
        sys.modules["ultralytics"] = ultralytics_stub

    # ---- faster_whisper --------------------------------------------------
    if "faster_whisper" not in sys.modules:
        fw_stub = types.ModuleType("faster_whisper")

        class _StubWhisperModel:
            def __init__(self, *args, **kwargs):
                pass

            def transcribe(self, path):
                segment = types.SimpleNamespace(text="stub transcription")
                info = types.SimpleNamespace(language="en")
                return [segment], info

        fw_stub.WhisperModel = _StubWhisperModel
        sys.modules["faster_whisper"] = fw_stub

    # ---- transformers (only the `pipeline` factory is used) -----------
    if "transformers" not in sys.modules:
        transformers_stub = types.ModuleType("transformers")

        class _StubLLMPipeline:
            """
            Mimics the shape of a HF chat-text-generation pipeline call:
            outputs[0]["generated_text"][-1]["content"] is what pipeline.py reads.
            Default behavior just echoes back a fixed string; tests that need a
            specific answer monkeypatch `pipeline.llm_pipeline` directly instead.
            """

            def __call__(self, messages, max_new_tokens=60, **kwargs):
                reply = {"role": "assistant", "content": "stub-object"}
                return [{"generated_text": list(messages) + [reply]}]

        def _pipeline_factory(task, model=None, dtype=None, device=None):
            return _StubLLMPipeline()

        transformers_stub.pipeline = _pipeline_factory
        sys.modules["transformers"] = transformers_stub

    # ---- gTTS --------------------------------------------------------
    if "gtts" not in sys.modules:
        gtts_stub = types.ModuleType("gtts")

        class _StubGTTS:
            def __init__(self, text="", lang="en"):
                self.text = text
                self.lang = lang

            def save(self, filename):
                # Write a tiny placeholder file; tests only check it exists.
                with open(filename, "wb") as f:
                    f.write(b"ID3-stub-mp3-bytes")

        gtts_stub.gTTS = _StubGTTS
        sys.modules["gtts"] = gtts_stub

    # ---- langdetect --------------------------------------------------
    if "langdetect" not in sys.modules:
        langdetect_stub = types.ModuleType("langdetect")

        def _detect(text):
            return "en"

        langdetect_stub.detect = _detect
        sys.modules["langdetect"] = langdetect_stub


_install_stub_modules()


@pytest.fixture(autouse=True)
def _reset_detection_models():
    """Ensure tests that swap out pipeline.detection_models don't leak into others."""
    import pipeline as pl

    original = dict(pl.detection_models)
    yield
    pl.detection_models = original
