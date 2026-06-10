"""Local transcription via faster-whisper.

Reads a local media file and returns the same shape the highlight generator
expects: {duration, segments[start, end, text]}.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

from ..config import (
    LOCAL_ASR_BACKEND,
    LOCAL_OUTPUT_DIR,
    LOCAL_SENSEVOICE_MODEL,
    LOCAL_WHISPER_DEVICE,
    LOCAL_WHISPER_MODEL,
)


def _resolve_asr_backend() -> str:
    backend = (LOCAL_ASR_BACKEND or "whisper").strip().lower()
    if backend in ("whisper", "faster-whisper", "faster_whisper"):
        return "whisper"
    if backend in ("sensevoice", "funasr", "fun-asr"):
        return "sensevoice"
    raise RuntimeError(
        f"Unknown LOCAL_ASR_BACKEND={backend!r}. Use 'whisper' or 'sensevoice'."
    )


def _transcript_cache_path(media_path: str, backend: str) -> Path:
    """Return the .srt cache path for a media file."""
    cache_dir = Path(LOCAL_OUTPUT_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{Path(media_path).stem}.{backend}.srt"


def _format_srt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_srt_timestamp(value: str) -> float:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", value.strip())
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {value!r}")
    hours, minutes, seconds, millis = map(int, match.groups())
    return hours * 3600 + minutes * 60 + seconds + (millis / 1000.0)


def _probe_duration(media_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        media_path,
    ]
    try:
        output = subprocess.check_output(cmd, text=True).strip()
        return float(output)
    except Exception:
        return 0.0


def _extract_audio_track(source_path: str, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        source_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def _seconds(value: object) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return 0.0
    if seconds > 1000:
        seconds /= 1000.0
    return max(0.0, seconds)


def _coerce_funasr_result(result: object) -> Dict:
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            return first
    if isinstance(result, dict):
        return result
    return {}


def _sentence_info_to_segments(sentence_info: object) -> list:
    if not isinstance(sentence_info, list):
        return []

    segments = []
    for sentence in sentence_info:
        if not isinstance(sentence, dict):
            continue

        start = _seconds(sentence.get("start", sentence.get("begin")))
        end = _seconds(sentence.get("end", sentence.get("stop")))
        text = str(sentence.get("text") or "").strip()
        if not text or end <= start:
            continue

        segments.append({"start": start, "end": end, "text": text})

    return segments


def _transcribe_whisper(media_path: str, language: Optional[str] = None) -> Dict:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "faster-whisper is required for --mode local whisper transcription. Install it with:\n"
            "    pip install -r requirements-local.txt"
        ) from e

    device = _resolve_device()
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"[transcribe/local] whisper model={LOCAL_WHISPER_MODEL} device={device}", flush=True)

    model = WhisperModel(LOCAL_WHISPER_MODEL, device=device, compute_type=compute_type)
    segments_iter, info = model.transcribe(
        media_path,
        language=language,
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    segments = []
    for s in segments_iter:
        segments.append({
            "start": float(s.start),
            "end": float(s.end),
            "text": (s.text or "").strip(),
        })

    duration = float(getattr(info, "duration", 0.0)) or (segments[-1]["end"] if segments else 0.0)
    print(f"[transcribe/local] {len(segments)} segments, {duration:.0f}s of audio", flush=True)
    return {"duration": duration, "segments": segments}


def _transcribe_sensevoice(media_path: str, language: Optional[str] = None) -> Dict:
    try:
        from funasr import AutoModel  # type: ignore
        from funasr.utils.postprocess_utils import rich_transcription_postprocess  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "funasr is required for --mode local when LOCAL_ASR_BACKEND=sensevoice. Install it with:\n"
            "    pip install -r requirements-local.txt"
        ) from e

    device = _resolve_device()
    sensevoice_device = "cuda:0" if device == "cuda" else device
    print(
        f"[transcribe/local] sensevoice model={LOCAL_SENSEVOICE_MODEL} device={sensevoice_device}",
        flush=True,
    )

    with tempfile.TemporaryDirectory(prefix="sensevoice-") as tmpdir:
        audio_path = Path(tmpdir) / f"{Path(media_path).stem}.wav"
        _extract_audio_track(media_path, audio_path)

        model = AutoModel(
            model=LOCAL_SENSEVOICE_MODEL,
            trust_remote_code=True,
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            punc_model="ct-punc",
            device=sensevoice_device,
        )
        result = model.generate(
            input=str(audio_path),
            cache={},
            language=(language or "auto"),
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )

    payload = _coerce_funasr_result(result)
    segments = _sentence_info_to_segments(payload.get("sentence_info"))
    if not segments:
        segments = _sentence_info_to_segments(payload.get("timestamp"))

    if not segments:
        text = rich_transcription_postprocess(str(payload.get("text") or "").strip())
        duration = _probe_duration(media_path)
        if text and duration > 0:
            segments = [{"start": 0.0, "end": duration, "text": text}]

    duration = _probe_duration(media_path)
    if not duration and segments:
        duration = segments[-1]["end"]

    print(f"[transcribe/local] {len(segments)} segments, {duration:.0f}s of audio", flush=True)
    if not segments:
        raise RuntimeError(
            "SenseVoice returned no usable sentence timestamps. Try another model or backend."
        )

    return {"duration": duration, "segments": segments}


def _write_srt_cache(media_path: str, transcript: Dict) -> Path:
    cache_path = _transcript_cache_path(media_path)
    lines = []
    for idx, segment in enumerate(transcript.get("segments", []), start=1):
        start = _format_srt_timestamp(float(segment["start"]))
        end = _format_srt_timestamp(float(segment["end"]))
        text = str(segment.get("text", "")).strip().replace("\r", "").replace("\n", " ")
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    cache_path.write_text("\n".join(lines), encoding="utf-8")
    return cache_path


def _load_srt_cache(cache_path: Path) -> Dict:
    content = cache_path.read_text(encoding="utf-8-sig").strip()
    if not content:
        return {"duration": 0.0, "segments": []}

    segments = []
    for block in re.split(r"\n\s*\n", content):
        lines = [line.strip("\ufeff") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if "-->" not in lines[0] and len(lines) > 1 and "-->" in lines[1]:
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[0].split("-->", 1)]
        text = "\n".join(lines[1:]).strip()
        segments.append(
            {
                "start": _parse_srt_timestamp(start_raw),
                "end": _parse_srt_timestamp(end_raw),
                "text": text,
            }
        )

    duration = segments[-1]["end"] if segments else 0.0
    return {"duration": duration, "segments": segments}


def _resolve_device() -> str:
    if LOCAL_WHISPER_DEVICE != "auto":
        return LOCAL_WHISPER_DEVICE
    try:
        import torch  # type: ignore
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def transcribe_local(media_path: str, language: Optional[str] = None) -> Dict:
    """Run the configured local ASR backend on a file path and cache as .srt."""
    backend = _resolve_asr_backend()
    cache_path = _transcript_cache_path(media_path, backend)
    if cache_path.exists():
        source_mtime = os.path.getmtime(media_path)
        cache_mtime = cache_path.stat().st_mtime
        if cache_mtime >= source_mtime:
            print(f"[transcribe/local] reusing cached transcript: {cache_path}", flush=True)
            cached = _load_srt_cache(cache_path)
            print(
                f"[transcribe/local] {len(cached['segments'])} cached segments, "
                f"{cached['duration']:.0f}s of audio",
                flush=True,
            )
            return cached

    transcript = _transcribe_whisper(media_path, language=language) if backend == "whisper" else _transcribe_sensevoice(media_path, language=language)
    cache_path = _write_srt_cache(media_path, transcript)
    print(f"[transcribe/local] wrote cache: {cache_path}", flush=True)
    return transcript
