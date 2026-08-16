#!/usr/bin/env python3
"""Transcript-first rough cutting for football livestreams.

The script deliberately produces original-frame, original-audio rough cuts only.
It ranks candidate windows from a timestamped transcript using the target creator's
editing grammar; it does not add captions, effects, music, or reframing.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]


DEFAULT_SIGNALS = {
    # A creator profile supplies domain-specific nouns.  The baseline merely
    # verifies that the speech contains meaningful text, so a new niche is not
    # discarded just because its vocabulary was absent from this repository.
    "topic": [r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}"],
    "stance": ["我觉得", "我说", "其实", "就是", "根本", "肯定", "不可能", "会不会", "应该", "别急", "懂不懂", "就这"],
    "payoff": ["结果", "没想到", "居然", "反而", "笑死", "哈哈", "爽", "可惜", "差一点", "打脸", "翻车"],
    "adaptation": ["谎言", "尊重", "上帝", "陛下", "大人", "没有人比", "没人比", "你以为", "你也不想想", "这就是"],
}


@dataclass
class Segment:
    start: float
    end: float
    text: str


def parse_srt(path: Path) -> list[Segment]:
    timestamp = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")

    def seconds(raw: str) -> float:
        match = timestamp.fullmatch(raw.strip())
        if not match:
            raise ValueError(f"Invalid SRT timestamp: {raw!r}")
        hour, minute, second, millisecond = map(int, match.groups())
        return hour * 3600 + minute * 60 + second + millisecond / 1000

    segments: list[Segment] = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        time_line = lines[1] if "-->" in lines[1] else lines[0]
        if "-->" not in time_line:
            continue
        start, end = [part.strip() for part in time_line.split("-->", 1)]
        text_start = 2 if time_line == lines[1] else 1
        segments.append(Segment(seconds(start), seconds(end), " ".join(lines[text_start:])))
    if not segments:
        raise ValueError(f"No valid segments found in {path}")
    return segments


def format_time(value: float) -> str:
    value = max(0, round(value))
    return f"{value // 3600:02d}:{(value % 3600) // 60:02d}:{value % 60:02d}"


def compile_signals(profile_path: Path | None) -> tuple[dict[str, re.Pattern[str]], dict[str, object]]:
    profile: dict[str, object] = {"creator": "默认足球直播风格", "signals": DEFAULT_SIGNALS}
    if profile_path:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    raw_signals = profile.get("signals", {})
    if not isinstance(raw_signals, dict):
        raise ValueError("creator profile signals must be an object")
    patterns: dict[str, re.Pattern[str]] = {}
    for name in ("topic", "stance", "payoff", "adaptation"):
        extra_terms = raw_signals.get(name) or []
        if not isinstance(extra_terms, list):
            extra_terms = []
        # Built-in topic signals intentionally contain a compact regex. Profile
        # phrases are escaped, then *added* rather than replacing the baseline.
        baseline = "|".join(str(term) for term in DEFAULT_SIGNALS[name])
        additions = "|".join(re.escape(str(term)) for term in extra_terms if str(term))
        patterns[name] = re.compile("|".join(part for part in (baseline, additions) if part))
    return patterns, profile


def score_text(text: str, patterns: dict[str, re.Pattern[str]]) -> tuple[int, list[str]]:
    labels: list[str] = []
    score = 0
    if patterns["topic"].search(text):
        score += 3
        labels.append("主题/人物")
    if patterns["stance"].search(text):
        score += 2
        labels.append("主播观点")
    if patterns["payoff"].search(text):
        score += 2
        labels.append("反转或反应")
    if patterns["adaptation"].search(text):
        score += 3
        labels.append("台词梗")
    return score, labels


def find_song_candidates(segments: list[Segment], profile: dict[str, object]) -> list[dict[str, Any]]:
    """Find complete singing blocks configured in a creator profile.

    This is intentionally transcript-driven and offline: the detector acts only
    when the transcription contains a configured singing/lyrics marker.  It
    then uses the same pause-boundary logic as spoken topics, but with a longer
    allowed duration so a song is never shortened to a generic short-video
    length.
    """
    special = profile.get("special_segments", {})
    if not isinstance(special, dict):
        return []
    song = special.get("song", {})
    if not isinstance(song, dict) or not song.get("enabled", False):
        return []
    keywords = [str(word).strip() for word in song.get("keywords", []) if str(word).strip()]
    exclude_keywords = [str(word).strip() for word in song.get("exclude_keywords", []) if str(word).strip()]
    if not keywords:
        return []
    pattern = re.compile("|".join(re.escape(word) for word in keywords))
    max_seconds = int(song.get("max_seconds", 600))
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    for index, segment in enumerate(segments):
        if any(word in segment.text for word in exclude_keywords):
            continue
        if not pattern.search(segment.text):
            continue
        bounds = topic_bounds(segments, index, max_seconds, pause_seconds=float(song.get("pause_seconds", 4)))
        if not bounds or bounds in seen:
            continue
        seen.add(bounds)
        start, end = bounds
        candidates.append(
            {
                "start_seconds": start,
                "end_seconds": end,
                "score": 100,
                "hook": segment.text[:42].strip() or "主播唱歌",
                "reason": "主播特长：完整歌曲",
                "context": " ".join(item.text for item in segments if start <= item.start and item.end <= end)[:500],
                "kind": "song",
            }
        )
    return candidates


def topic_bounds(segments: list[Segment], anchor_index: int, max_seconds: int, pause_seconds: float = 4.0) -> tuple[float, float] | None:
    """Return a complete speech block around an anchor, never a padded time window.

    Whisper segments are usually sentence-like fragments.  A pause of several
    seconds is the most reliable offline marker that the streamer has changed
    topic.  Keeping the whole block prevents a clip from starting mid-question
    or ending before the speaker's conclusion.
    """
    first = anchor_index
    while first > 0 and segments[first].start - segments[first - 1].end < pause_seconds:
        first -= 1
    last = anchor_index
    while last + 1 < len(segments) and segments[last + 1].start - segments[last].end < pause_seconds:
        last += 1
    start, end = segments[first].start, segments[last].end
    # Do not silently chop a long, still-active topic just to meet the former
    # 45–120 second target.  It is better to leave it for manual review.
    if end - start > max_seconds:
        return None
    return start, end


def make_candidates(
    segments: list[Segment],
    min_seconds: int,
    max_seconds: int,
    patterns: dict[str, re.Pattern[str]],
    boundary_segments: list[Segment] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    boundary_segments = boundary_segments or segments
    for index, segment in enumerate(segments):
        nearby = segments[max(0, index - 3) : min(len(segments), index + 7)]
        context = " ".join(item.text for item in nearby)
        score, labels = score_text(context, patterns)
        if score < 5 or len(labels) < 2:
            continue
        anchor = max(nearby, key=lambda item: score_text(item.text, patterns)[0])
        anchor_index = boundary_segments.index(anchor)
        bounds = topic_bounds(boundary_segments, anchor_index, max_seconds)
        if not bounds:
            continue
        start, end = bounds
        if end - start < min_seconds:
            continue
        hook = anchor.text[:42].strip() or "直播反应片段"
        candidates.append(
            {
                "start_seconds": start,
                "end_seconds": end,
                "score": score,
                "hook": hook,
                "reason": "、".join(labels) + "、完整话题段",
                "context": context[:500],
            }
        )

    return candidates


def choose_candidates(candidates: list[dict[str, Any]], max_clips: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    songs = [item for item in candidates if item.get("kind") == "song"]
    regular = [item for item in candidates if item.get("kind") != "song"]
    # Every detected song is a creator-specific must-export.  --max-clips only
    # limits the ordinary football/commentary selections.
    for candidate in sorted(songs, key=lambda item: item["start_seconds"]):
        overlaps = any(
            max(candidate["start_seconds"], kept["start_seconds"])
            < min(candidate["end_seconds"], kept["end_seconds"])
            for kept in selected
        )
        if not overlaps:
            selected.append(candidate)
    normal_count = 0
    for candidate in sorted(regular, key=lambda item: item["score"], reverse=True):
        overlaps = any(
            max(candidate["start_seconds"], kept["start_seconds"])
            < min(candidate["end_seconds"], kept["end_seconds"])
            for kept in selected
        )
        if not overlaps:
            selected.append(candidate)
            normal_count += 1
        if normal_count >= max_clips:
            break

    formatted: list[dict[str, Any]] = []
    for index, candidate in enumerate(selected, start=1):
        item = dict(candidate)
        item["id"] = f"{index:02d}"
        item["start"] = format_time(item.pop("start_seconds"))
        item["end"] = format_time(item.pop("end_seconds"))
        formatted.append(item)
    return formatted


def analyze_hourly(segments: list[Segment], window_seconds: int, per_hour: int, min_seconds: int, max_seconds: int, patterns: dict[str, re.Pattern[str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    duration = segments[-1].end
    hourly: list[dict[str, Any]] = []
    all_candidates: list[dict[str, Any]] = []
    for hour_start in range(0, int(duration) + 1, window_seconds):
        hour_end = min(duration, hour_start + window_seconds)
        hour_segments = [segment for segment in segments if segment.end > hour_start and segment.start < hour_end]
        if not hour_segments:
            continue
        # Candidate discovery remains hourly, but topic boundaries must be
        # calculated against the full transcript so an ongoing thought is not
        # chopped merely because it crosses an hour boundary.
        candidates = make_candidates(hour_segments, min_seconds, max_seconds, patterns, boundary_segments=segments)
        all_candidates.extend(candidates)
        hourly.append(
            {
                "start": format_time(hour_start),
                "end": format_time(hour_end),
                "candidate_count": len(candidates),
                "top_candidates": choose_candidates(candidates, per_hour),
            }
        )
    return hourly, all_candidates


def download_source(url: str, output: Path, height: int) -> Path:
    source_dir = output / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    target = source_dir / "source.%(ext)s"
    format_selector = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
    # Invoke the installed module instead of assuming a console-script wrapper exists.
    # Some virtual environments retain the package but do not expose `.venv/bin/yt-dlp`.
    subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--no-playlist", "-f", format_selector, "--merge-output-format", "mp4", "-o", str(target), url],
        check=True,
    )
    source = source_dir / "source.mp4"
    if not source.is_file():
        matches = list(source_dir.glob("source.*"))
        if len(matches) != 1:
            raise RuntimeError("Could not determine the downloaded source file")
        source = matches[0]
    return source


def get_transcript(input_path: Path, transcript_srt: Path | None, language: str) -> list[Segment]:
    if transcript_srt:
        return parse_srt(transcript_srt)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from local.transcriber import transcribe_local

    raw = transcribe_local(str(input_path), language=language)
    return [Segment(float(item["start"]), float(item["end"]), str(item["text"])) for item in raw["segments"]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create hourly transcript-ranked football livestream rough cuts.")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", type=Path, help="Local MP4/MKV livestream recording")
    source_group.add_argument("--input-url", help="Public video URL to download before transcription")
    parser.add_argument("--output", required=True, type=Path, help="Output directory")
    parser.add_argument("--transcript-srt", type=Path, help="Reuse an existing timestamped SRT")
    parser.add_argument("--creator-profile", type=Path, help="Style profile JSON from profiles/ or analyze_creator_profile.py")
    parser.add_argument("--language", default="zh", help="Whisper language code when transcribing")
    parser.add_argument("--max-clips", type=int, default=5)
    parser.add_argument("--analysis-window-seconds", type=int, default=3600, help="Transcript analysis window; defaults to one hour")
    parser.add_argument("--candidates-per-window", type=int, default=5, help="Hourly candidates retained in hourly-analysis.json")
    parser.add_argument("--download-height", type=int, default=720, help="Maximum download height for --input-url; defaults to 720p")
    parser.add_argument("--min-seconds", type=int, default=45)
    parser.add_argument("--max-seconds", type=int, default=120)
    parser.add_argument("--export", action="store_true", help="Export MP4 rough cuts after writing the plan")
    parser.add_argument("--reencode", action="store_true", help="Use accurate, slower boundary cuts")
    args = parser.parse_args()

    if args.input and not args.input.is_file():
        parser.error(f"input not found: {args.input}")
    if args.transcript_srt and not args.transcript_srt.is_file():
        parser.error(f"transcript not found: {args.transcript_srt}")
    if args.creator_profile and not args.creator_profile.is_file():
        parser.error(f"creator profile not found: {args.creator_profile}")
    if args.min_seconds <= 0 or args.max_seconds < args.min_seconds or args.analysis_window_seconds <= 0:
        parser.error("set positive durations with --max-seconds >= --min-seconds")

    args.output.mkdir(parents=True, exist_ok=True)
    source = args.input or download_source(args.input_url, args.output, args.download_height)
    patterns, profile = compile_signals(args.creator_profile)
    segments = get_transcript(source, args.transcript_srt, args.language)
    transcript_path = args.output / "transcript.json"
    transcript_path.write_text(
        json.dumps({"duration": segments[-1].end, "segments": [item.__dict__ for item in segments]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    hourly, all_candidates = analyze_hourly(
        segments,
        args.analysis_window_seconds,
        args.candidates_per_window,
        args.min_seconds,
        args.max_seconds,
        patterns,
    )
    all_candidates.extend(find_song_candidates(segments, profile))
    hourly_path = args.output / "hourly-analysis.json"
    hourly_path.write_text(json.dumps({"window_seconds": args.analysis_window_seconds, "windows": hourly}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    clips = choose_candidates(all_candidates, args.max_clips)
    if not clips:
        raise SystemExit("No candidate matched two or more style signals; review the transcript or expand the keyword rules.")
    plan = {"title": source.stem, "source": str(source), "creator": profile.get("creator"), "creator_profile": str(args.creator_profile) if args.creator_profile else None, "resolution_target": f"{args.download_height}p", "clips": clips}
    plan_path = args.output / "candidate-cut-plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.export:
        command = [sys.executable, str(Path(__file__).with_name("rough_cut.py")), "--input", str(source), "--plan", str(plan_path), "--output", str(args.output / "exports")]
        if args.reencode:
            command.append("--reencode")
        subprocess.run(command, check=True)

    print(json.dumps({"source": str(source), "transcript": str(transcript_path), "hourly_analysis": str(hourly_path), "plan": str(plan_path), "candidates": clips}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
