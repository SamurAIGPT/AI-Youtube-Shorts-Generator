"""End-to-end orchestrator.

Three modes:
  * mode="api"   (default) — MuAPI does download / transcribe / LLM / autocrop.
                              Fast, no local deps, pay-per-call.
  * mode="local"            — yt-dlp + faster-whisper + OpenAI or Gemini + ffmpeg/opencv.
                              Self-hosted, LLM_PROVIDER selects OpenAI or Gemini.
  * mode="self"             — uses externally supplied highlight moments to crop clips.
                              Great when you already know the best moments and want to skip LLM.
"""
from typing import Dict, List, Optional

from .downloader import download_youtube
from .highlights import call_muapi_llm, get_highlights
from .transcriber import transcribe


def _run_local(
    youtube_url: str,
    num_clips: int,
    aspect_ratio: str,
    download_format: str,
    language: Optional[str],
) -> Dict:
    from .local.clipper import crop_highlights_local
    from .local.downloader import download_youtube_local
    from .local.llm import call_local_llm
    from .local.transcriber import transcribe_local

    source_path = download_youtube_local(youtube_url, fmt=download_format)

    transcript = transcribe_local(source_path, language=language)
    if not transcript["segments"]:
        raise RuntimeError(
            "Whisper produced no segments. The video may have no detectable speech."
        )

    highlights_result = get_highlights(transcript, num_clips=num_clips, llm_fn=call_local_llm)
    all_highlights: List[Dict] = highlights_result.get("highlights", [])
    if not all_highlights:
        raise RuntimeError("Highlight generator returned zero clips.")

    top = sorted(all_highlights, key=lambda h: int(h.get("score", 0)), reverse=True)[:num_clips]
    print(f"[pipeline/local] cropping {len(top)} of {len(all_highlights)} candidates", flush=True)

    shorts = crop_highlights_local(source_path, top, aspect_ratio=aspect_ratio)

    return {
        "mode": "local",
        "source_video_url": source_path,
        "transcript": transcript,
        "highlights": all_highlights,
        "shorts": shorts,
    }


def _run_self(
    youtube_url: str,
    num_clips: int,
    aspect_ratio: str,
    download_format: str,
    self_highlights: Optional[List[Dict]],
) -> Dict:
    from .local.clipper import crop_highlights_local
    from .local.downloader import download_youtube_local

    source_path = download_youtube_local(youtube_url, fmt=download_format)

    if not self_highlights:
        raise RuntimeError("Mode 'self' requires --self-highlights with at least one highlight moment.")

    normalized = []
    for item in self_highlights[:num_clips * 3]:
        normalized.append(
            {
                "title": str(item.get("title") or "Manual highlight").strip(),
                "start_time": float(item["start_time"]),
                "end_time": float(item["end_time"]),
                "score": int(item.get("score", 100)),
                "hook_sentence": str(item.get("hook_sentence") or "").strip() or "Manual highlight",
                "virality_reason": str(item.get("virality_reason") or "User supplied highlight").strip(),
            }
        )

    top = normalized[:num_clips]
    print(f"[pipeline/self] cropping {len(top)} supplied highlights", flush=True)
    shorts = crop_highlights_local(source_path, top, aspect_ratio=aspect_ratio)

    return {
        "mode": "self",
        "source_video_url": source_path,
        "transcript": {"segments": []},
        "highlights": normalized,
        "shorts": shorts,
    }


def _run_api(
    youtube_url: str,
    num_clips: int,
    aspect_ratio: str,
    download_format: str,
    language: Optional[str],
) -> Dict:
    source_url = download_youtube(youtube_url, fmt=download_format)

    transcript = transcribe(source_url, language=language)
    if not transcript["segments"]:
        raise RuntimeError(
            "Whisper produced no segments. The video may have no detectable speech."
        )

    highlights_result = get_highlights(transcript, num_clips=num_clips, llm_fn=call_muapi_llm)
    all_highlights: List[Dict] = highlights_result.get("highlights", [])
    if not all_highlights:
        raise RuntimeError("Highlight generator returned zero clips.")

    top = sorted(all_highlights, key=lambda h: int(h.get("score", 0)), reverse=True)[:num_clips]
    print(f"[pipeline] cropping {len(top)} of {len(all_highlights)} candidates", flush=True)

    shorts = crop_highlights(source_url, top, aspect_ratio=aspect_ratio)

    return {
        "mode": "api",
        "source_video_url": source_url,
        "transcript": transcript,
        "highlights": all_highlights,
        "shorts": shorts,
    }


def generate_shorts(
    youtube_url: str,
    num_clips: int = 3,
    aspect_ratio: str = "9:16",
    download_format: str = "720",
    language: Optional[str] = None,
    mode: str = "api",
    self_highlights: Optional[List[Dict]] = None,
) -> Dict:
    """Run the full pipeline and return a structured result.

    Args:
        youtube_url: source URL.
        num_clips: how many shorts to render.
        aspect_ratio: e.g. "9:16", "1:1".
        download_format: source resolution ("360" / "480" / "720" / "1080").
        language: ISO-639-1 to force Whisper language detection.
        mode: "api" (default, MuAPI), "local" (yt-dlp + faster-whisper +
            OpenAI or Gemini + ffmpeg), or "self" (use externally supplied highlights).

    Returns:
        {
          "mode": "api" | "local",
          "source_video_url": str,   # hosted URL (api) or local path (local)
          "transcript": {...},
          "highlights": [...],       # all candidates ranked
          "shorts": [...],           # top `num_clips` with clip_url / local path
        }
    """
    mode = (mode or "api").lower()
    if mode == "local":
        return _run_local(youtube_url, num_clips, aspect_ratio, download_format, language)
    if mode == "self":
        return _run_self(youtube_url, num_clips, aspect_ratio, download_format, self_highlights)
    if mode == "api":
        return _run_api(youtube_url, num_clips, aspect_ratio, download_format, language)
    raise ValueError(f"Unknown mode: {mode!r}. Use 'api' or 'local'.")
