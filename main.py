"""CLI entry point.

Usage:
    python main.py "https://www.youtube.com/watch?v=..." \
        --num-clips 5 --aspect-ratio 9:16
"""
import argparse
import json
import os
import sys

# Windows uses 'charmap' by default, which can't encode Unicode characters
# like →. Reconfigure stdout/stderr to UTF-8 so output works on all platforms.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from shorts_generator import generate_shorts


def _load_self_highlights(raw_value: str | None):
    if not raw_value:
        return None

    candidate = raw_value.strip()
    if not candidate:
        return None

    if os.path.exists(candidate):
        with open(candidate, "r", encoding="utf-8") as handle:
            candidate = handle.read()

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse --self-highlights as JSON: {exc}") from exc

    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("--self-highlights must be a JSON array of highlight objects")

    normalized = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each highlight entry must be an object")
        start_time = item.get("start_time", item.get("start", 0))
        end_time = item.get("end_time", item.get("end", start_time))
        try:
            start_time = float(start_time)
            end_time = float(end_time)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid time values in highlight entry: {item}") from exc
        if end_time <= start_time:
            raise ValueError(f"Highlight end time must be greater than start time: {item}")

        normalized.append(
            {
                "title": str(item.get("title") or "Manual highlight").strip(),
                "start_time": start_time,
                "end_time": end_time,
                "score": int(item.get("score", 100)),
                "hook_sentence": str(item.get("hook_sentence") or "").strip() or "Manual highlight",
                "virality_reason": str(item.get("virality_reason") or "User supplied highlight").strip(),
            }
        )

    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="AI YouTube Shorts Generator")
    parser.add_argument("url", help="YouTube URL, file:// URL, or local file path")
    parser.add_argument(
        "--mode",
        choices=["api", "local", "self"],
        default="api",
        help="api (default, MuAPI), local (Whisper + LLM + ffmpeg), or self (use externally supplied highlight moments).",
    )
    parser.add_argument("--num-clips", type=int, default=3, help="How many shorts to render (default: 3)")
    parser.add_argument("--aspect-ratio", default="9:16", help="Output aspect ratio (default: 9:16)")
    parser.add_argument("--format", default="720", help="Source download resolution: 360 / 480 / 720 / 1080 (default: 720)")
    parser.add_argument("--language", default=None, help="Force Whisper language code, e.g. 'en' (default: auto-detect)")
    parser.add_argument("--output-json", default=None, help="Write the full result JSON to this path")
    parser.add_argument(
        "--self-highlights",
        default=None,
        help="JSON array or path to a JSON file with manual highlight moments, e.g. [{\"start_time\": 10, \"end_time\": 25, \"title\": \"Intro\"}]",
    )
    args = parser.parse_args()

    try:
        result = generate_shorts(
            youtube_url=args.url,
            num_clips=args.num_clips,
            aspect_ratio=args.aspect_ratio,
            download_format=args.format,
            language=args.language,
            mode=args.mode,
            self_highlights=_load_self_highlights(args.self_highlights),
        )
    except Exception as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1

    print("\n" + "=" * 72)
    print(f"Mode:          {result.get('mode', args.mode)}")
    print(f"Source video:  {result['source_video_url']}")
    print(f"Highlights:    {len(result['highlights'])} candidates → kept top {len(result['shorts'])}")
    print("=" * 72)
    for i, s in enumerate(result["shorts"], 1):
        print(f"\n#{i}  score={s.get('score')}  {s.get('start_time'):.1f}s → {s.get('end_time'):.1f}s")
        print(f"     title:  {s.get('title')}")
        print(f"     hook:   {s.get('hook_sentence')}")
        if s.get("clip_url"):
            print(f"     clip:   {s['clip_url']}")
        else:
            print(f"     clip:   FAILED ({s.get('error')})")

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nFull JSON written to {args.output_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
