"""Defaults for the skill's local runtime; no remote service is used."""

LOCAL_WHISPER_MODEL = "base"
LOCAL_WHISPER_DEVICE = "auto"  # auto / cpu / cuda
LOCAL_OUTPUT_DIR = "output"
LOCAL_TRANSCRIBER_BACKEND = "faster-whisper"
WHISPER_CPP_COMMAND = "whisper-cli"
WHISPER_CPP_MODEL = "models/ggml-base.bin"

# VAD (Voice Activity Detection) settings for faster-whisper
# Default threshold is 0.5; lower = more sensitive, higher = less sensitive
# Default min_speech_duration_ms is 250ms; increase to avoid tiny false positives
# Default min_silence_duration_ms is 2000ms; increase to avoid splitting mid-sentence
# DISABLED by default because VAD is too aggressive on mixed speech/music content
LOCAL_WHISPER_VAD_FILTER = False
LOCAL_WHISPER_VAD_PARAMETERS = {
    "threshold": 0.5,
    "min_speech_duration_ms": 250,
    "max_speech_duration_s": float("inf"),
    "min_silence_duration_ms": 2000,
    "speech_pad_ms": 400,
}
