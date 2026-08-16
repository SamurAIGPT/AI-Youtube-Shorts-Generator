#!/usr/bin/env python3
"""One-command creator workflow: profile, hourly ranking, and rough cuts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analyze_creator_profile import build_creator_profile
from transcript_rough_cut import (
    Segment,
    analyze_hourly,
    choose_candidates,
    compile_signals,
    find_song_candidates,
    get_transcript,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = Path(__file__).resolve().parent


def _write_srt(path: Path, segments: list[Segment]) -> None:
    def stamp(value: float) -> str:
        milliseconds = round(value * 1000)
        seconds, ms = divmod(milliseconds, 1000)
        minutes, second = divmod(seconds, 60)
        hour, minute = divmod(minutes, 60)
        return f"{hour:02d}:{minute:02d}:{second:02d},{ms:03d}"

    blocks = [f"{i}\n{stamp(item.start)} --> {stamp(item.end)}\n{item.text}" for i, item in enumerate(segments, 1)]
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def _load_feedback(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid clip feedback JSON: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("clip feedback must be a JSON object")
    return payload


def _apply_feedback(candidates: list[dict], feedback: dict) -> list[dict]:
    """Apply user-maintained keyword preferences without hiding the reason."""
    preferences = feedback.get("preferences", {})
    if not isinstance(preferences, dict):
        return candidates
    boost = [str(item).strip() for item in preferences.get("boost_keywords", []) if str(item).strip()]
    suppress = [str(item).strip() for item in preferences.get("suppress_keywords", []) if str(item).strip()]
    ranked: list[dict] = []
    for candidate in candidates:
        context = str(candidate.get("context", ""))
        if any(keyword in context for keyword in suppress):
            continue
        matches = [keyword for keyword in boost if keyword in context]
        item = dict(candidate)
        if matches:
            item["score"] = int(item.get("score", 0)) + (2 * len(matches))
            item["reason"] = f"{item.get('reason', '')}、人工反馈偏好（{'、'.join(matches)}）".strip("、")
        ranked.append(item)
    return ranked


def _write_feedback_template(path: Path, creator: str, clips: list[dict], existing: dict) -> None:
    if existing:
        return
    template = {
        "creator": creator,
        "instructions": "填写 feedback 中每段的 decision/reason；把会出现在未来字幕中的词填入 preferences，以影响下次选段。",
        "preferences": {"boost_keywords": [], "suppress_keywords": []},
        "feedback": [
            {
                "clip_id": clip.get("id"),
                "decision": "undecided",
                "reason": "",
                "keywords": [],
                "suggested_start": clip.get("start"),
                "suggested_end": clip.get("end"),
            }
            for clip in clips
        ],
    }
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_workflow(
    target_url: str,
    creator: str,
    output: Path,
    history_urls: list[str] | None = None,
    history_srt: list[Path] | None = None,
    target_srt: Path | None = None,
    creator_profile: Path | None = None,
    clip_feedback: Path | None = None,
    note: str = "",
    language: str = "zh",
    max_clips: int = 5,
    window_seconds: int = 3600,
    candidates_per_window: int = 5,
    download_height: str = "720",
    export: bool = False,
    reencode: bool = False,
) -> dict:
    """Run the reproducible workflow; transcript paths make it testable offline."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    from local.downloader import download_video

    output.mkdir(parents=True, exist_ok=True)
    if creator_profile:
        if not creator_profile.is_file():
            raise ValueError(f"Creator profile not found: {creator_profile}")
        profile_path = creator_profile
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    else:
        history_dir = output / "history-transcripts"
        history_dir.mkdir(exist_ok=True)
        profile_inputs = list(history_srt or [])
        for index, url in enumerate(history_urls or [], 1):
            media = str(Path(download_video(url, fmt=download_height, out_dir=str(output / "history-source"))).resolve())
            segments = get_transcript(Path(media), None, language)
            transcript_path = history_dir / f"history-{index:02d}.srt"
            _write_srt(transcript_path, segments)
            profile_inputs.append(transcript_path)
        if not profile_inputs:
            raise ValueError("Provide --creator-profile, --history-url, or --history-transcript-srt.")
        profile = build_creator_profile(creator, profile_inputs, note)
        profile_path = output / "creator-profile.json"
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    source = str(Path(download_video(target_url, fmt=download_height, out_dir=str(output / "source"))).resolve())
    segments = get_transcript(Path(source), target_srt, language)
    if not segments:
        raise ValueError("Target transcript contains no speech segments.")
    (output / "transcript.json").write_text(
        json.dumps({"duration": segments[-1].end, "segments": [item.__dict__ for item in segments]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    feedback_path = clip_feedback or (output / "clip-feedback.json")
    feedback = _load_feedback(feedback_path)
    patterns, profile = compile_signals(profile_path)
    # Complete topic blocks are preferred over an arbitrary 45–120 second
    # padded window.  Short but self-contained replies remain eligible; a
    # still-active topic over three minutes is left for manual review instead
    # of being cut in the middle.
    hourly, candidates = analyze_hourly(segments, window_seconds, candidates_per_window, 15, 180, patterns)
    candidates.extend(find_song_candidates(segments, profile))
    candidates = _apply_feedback(candidates, feedback)
    hourly_path = output / "hourly-analysis.json"
    hourly_path.write_text(json.dumps({"window_seconds": window_seconds, "windows": hourly}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    clips = choose_candidates(candidates, max_clips)
    _write_feedback_template(feedback_path, profile.get("creator", creator), clips, feedback)
    plan = {"title": Path(source).stem, "source": source, "creator": profile.get("creator", creator), "creator_profile": str(profile_path), "clips": clips}
    plan_path = output / "candidate-cut-plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    exports: list[str] = []
    if export and clips:
        from rough_cut import main as rough_cut_main
        old_argv = sys.argv
        try:
            sys.argv = ["rough_cut.py", "--input", source, "--plan", str(plan_path), "--output", str(output / "exports")] + (["--reencode"] if reencode else [])
            rough_cut_main()
        finally:
            sys.argv = old_argv
        exports = [str(path) for path in sorted((output / "exports").glob("*.mp4"))]
    return {"creator_profile": str(profile_path), "hourly_analysis": str(hourly_path), "plan": str(plan_path), "clip_feedback": str(feedback_path), "clips": clips, "exports": exports}


def main() -> int:
    parser = argparse.ArgumentParser(description="多平台长视频一键：爆款画像 → 每小时筛选 → 粗剪。")
    parser.add_argument("target_url", help="yt-dlp 支持的公开视频/直播回放链接（也支持本地文件）")
    parser.add_argument("--creator", required=True, help="博主/账号名称")
    parser.add_argument("--history-url", action="append", default=[], help="已确认的历史爆款视频链接；可重复传入")
    parser.add_argument("--history-transcript-srt", type=Path, action="append", default=[], help="历史爆款 SRT；适合离线复跑")
    parser.add_argument("--creator-profile", type=Path, help="复用已保存的主播画像 JSON，跳过历史视频分析")
    parser.add_argument("--clip-feedback", type=Path, help="读取既有 clip-feedback.json；首次运行会在输出目录创建模板")
    parser.add_argument("--target-transcript-srt", type=Path, help="复用目标 SRT，跳过目标转录")
    parser.add_argument("--output", type=Path, required=True, help="本次任务输出目录")
    parser.add_argument("--note", default="", help="账号定位/人工观察")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--max-clips", type=int, default=5)
    parser.add_argument("--analysis-window-seconds", type=int, default=3600)
    parser.add_argument("--candidates-per-window", type=int, default=5)
    parser.add_argument("--format", default="720")
    parser.add_argument("--export", action="store_true", help="按选段计划导出 MP4 粗剪")
    parser.add_argument("--reencode", action="store_true", help="粗剪采用更准确但更慢的重编码")
    args = parser.parse_args()
    try:
        result = run_workflow(args.target_url, args.creator, args.output, args.history_url, args.history_transcript_srt, args.target_transcript_srt, args.creator_profile, args.clip_feedback, args.note, args.language, args.max_clips, args.analysis_window_seconds, args.candidates_per_window, args.format, args.export, args.reencode)
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
