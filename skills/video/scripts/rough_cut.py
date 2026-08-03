#!/usr/bin/env python3
"""Export original-frame rough cuts from a timestamped cut plan."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return cleaned[:64] or "clip"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export rough-cut clips without changing frame or audio.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reencode", action="store_true", help="Accurate cuts; preserves the original frame dimensions")
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"input not found: {args.input}")
    if not args.plan.is_file():
        parser.error(f"plan not found: {args.plan}")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    clips = plan.get("clips", [])
    if not clips:
        parser.error("plan has no clips")

    args.output.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    for index, clip in enumerate(clips, start=1):
        start, end = clip.get("start"), clip.get("end")
        if not start or not end:
            raise ValueError(f"clip {index} requires start and end")
        label = safe_name(str(clip.get("hook", "clip")))
        target = args.output / f"{clip.get('id', f'{index:02d}')}_{label}.mp4"
        command = ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", str(args.input)]
        if args.reencode:
            command.extend(["-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k"])
        else:
            command.extend(["-map", "0", "-c", "copy"])
        command.append(str(target))
        subprocess.run(command, check=True)
        outputs.append(str(target))
    print(json.dumps({"exports": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
