#!/usr/bin/env python3
"""Build a transparent creator-style profile from supplied timestamped transcripts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from transcript_rough_cut import parse_srt


COMMON_WORDS = {"这个", "就是", "然后", "我们", "你们", "他们", "没有", "一个", "什么", "因为", "所以", "现在", "真的", "可以", "可能", "还是", "一下"}


def phrases(text: str) -> list[str]:
    parts = re.split(r"[，。！？!?、\n]+", text)
    return [part.strip() for part in parts if 4 <= len(part.strip()) <= 22]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze supplied creator transcripts into a reusable cutting profile.")
    parser.add_argument("--creator", required=True, help="Creator/account name")
    parser.add_argument("--transcript-srt", required=True, type=Path, action="append", help="One or more supplied SRT files")
    parser.add_argument("--output", required=True, type=Path, help="Creator profile JSON")
    parser.add_argument("--note", default="", help="Optional user-provided account positioning")
    args = parser.parse_args()
    if any(not path.is_file() for path in args.transcript_srt):
        parser.error("every --transcript-srt file must exist")

    all_text = " ".join(segment.text for path in args.transcript_srt for segment in parse_srt(path))
    phrase_counts = Counter(phrases(all_text))
    words = Counter(word for word in re.findall(r"[\u4e00-\u9fff]{2,}", all_text) if word not in COMMON_WORDS)
    profile = {
        "creator": args.creator,
        "analysis_basis": {
            "transcripts": [str(path) for path in args.transcript_srt],
            "note": args.note,
            "method": "只统计用户提供的文字稿；候选高频短语需人工确认后再作为剪辑信号。"
        },
        "observed_style": {
            "repeated_phrases": [item for item, _ in phrase_counts.most_common(20)],
            "frequent_terms": [item for item, _ in words.most_common(30)]
        },
        "signals": {"topic": [], "stance": [], "payoff": [], "adaptation": []},
        "selection_rule": "先人工补充 signals，再用于自动粗剪；避免只按高频口头禅截取。"
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profile": str(args.output), "transcripts_analyzed": len(args.transcript_srt)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
