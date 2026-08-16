---
name: creator-video-clipping
description: Analyze a creator's supplied high-performing video transcripts into a reusable style profile, then transcript-first select and export complete-topic rough cuts from that creator's long videos or livestreams. Use for personalized creator analysis, long-video clipping, hourly transcript analysis, clip feedback iteration, or preserving detected full-song segments. Do not use for captions, effects, color grading, sound design, or fine editing.
---

# Creator Style Analysis + Long-video Rough Cut

Turn creator-owned or user-authorized transcript samples into a transparent style profile, then select complete-topic rough cuts from a supplied recording.

## Build or review the creator profile

Analyze only source material the user supplies or authorizes for download. Use three to four representative high-performing videos when available:

```bash
.venv/bin/python skills/video/scripts/analyze_creator_profile.py \
  --creator '创作者名称' \
  --transcript-srt /path/to/video-1.srt \
  --transcript-srt /path/to/video-2.srt \
  --output /path/to/creator-profile.json
```

Review the generated `signals.topic`, `signals.stance`, `signals.payoff`, and `signals.adaptation`. Retain only traits that distinguish this creator. Start from `profiles/example-creator-profile.json` when creating a profile by hand.

Use `special_segments.song` only for creators whose singing should be kept. Configure clear speech markers such as “我唱” or “唱一首”; exclude markers such as “点歌” or “放歌” when they merely mean music playback.

## Run the workflow

Use the project virtual environment and the one-command workflow:

```bash
.venv/bin/python main.py video-workflow '待剪视频链接或本地文件' \
  --creator '创作者名称' \
  --history-url '历史爆款链接 1' \
  --history-url '历史爆款链接 2' \
  --output output/本次任务 \
  --export --reencode
```

For offline reruns, pass `--history-transcript-srt` and `--target-transcript-srt`. To reuse an existing profile, pass `--creator-profile /path/to/creator-profile.json`.

The workflow produces a transcript, hourly analysis, `candidate-cut-plan.json`, and `clip-feedback.json`. On later runs, pass `--clip-feedback` to promote or suppress patterns the creator's editor approves or rejects.

## Selection and export rules

- Select complete topic blocks: start at the topic setup and end at a natural pause or conclusion. Do not pad to a fixed duration or cut a continuing viewpoint in half.
- Prefer the creator's profile signals plus a clear setup, viewpoint, reaction, reversal, or payoff.
- Export every detected full-song segment configured in `special_segments.song`; songs do not consume the ordinary `--max-clips` limit.
- Present a plan before exporting unless the user explicitly requests export.
- Preserve source picture and audio. Do not add captions, music, transitions, reframing, or other fine-editing effects.

Use `scripts/rough_cut.py --reencode` when timestamp accuracy matters. Report the output directory, exported file names, and the reasons in the cut plan.
