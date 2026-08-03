---
name: video
description: Analyze a creator account's supplied transcript samples into a reusable style profile, then select and export transcript-first rough cuts from livestreams that match that creator's traits. Use for creator/account feature analysis, personalized livestream clipping, hourly analysis of long livestreams, or the configured example "足球需要100个特兰". Do not use for captions, effects, color grading, sound design, or fine editing.
---

# Creator Style Analysis + Livestream Rough Cut

Turn supplied account samples into a transparent creator-style profile, then use it to turn a livestream into a small set of reviewable rough-cut clips. The configured example profile is `profiles/football-100-telan.json`: football event or player + strong host take + reaction/reversal + optional film/TV dialogue adaptation.

## Account Analysis

Analyze only content the user supplies or authorizes for download. An account homepage is not permission to silently fetch its entire history. For three to four representative videos, obtain their timestamped SRT files and run:

```bash
.venv/bin/python skills/video/scripts/analyze_creator_profile.py \
  --creator '博主名称' \
  --transcript-srt /path/to/video-1.srt \
  --transcript-srt /path/to/video-2.srt \
  --output skills/video/profiles/博主名称.json
```

The generated profile exposes frequent terms and repeated phrases for review. Edit its `signals.topic`, `signals.stance`, `signals.payoff`, and `signals.adaptation` to retain only genuinely distinctive traits before cutting. This keeps the selection explainable instead of treating generic high-frequency words as a personal style.

## Transcript First

Select clips from timestamped speech, not from thumbnail sampling or audio volume alone. Prefer the existing local transcriber at `shorts_generator/local/transcriber.py`: `transcribe_local()` uses `faster-whisper` and writes a reusable `.srt` cache in `output/`.

Use the transcript to find a setup, the host's football stance, a reversal or reaction, and a self-contained payoff. Read the matching source segment only to confirm the video boundary and that the joke lands visually.

Do **not** call `shorts_generator.pipeline.generate_shorts()` for this workflow. Its default path ranks generic viral highlights and can crop/reframe clips; this skill must retain the original frame and use the football-specific rules below.

Use `scripts/transcript_rough_cut.py` for the local pipeline. It can reuse an existing SRT or call the project's local Whisper transcriber. It analyzes the transcript in one-hour windows by default, writes `hourly-analysis.json` plus a ranked `candidate-cut-plan.json`, and exports only when `--export` is supplied.

## Scope

Do only these things:

1. Download or locate the supplied recording.
2. Generate or load its timestamped transcript.
3. Select moments that fit the target grammar.
3. Produce a cut plan for the user to approve, unless the user explicitly asks to export immediately.
4. Download a public URL when `yt-dlp` is installed and permitted, then export the selected ranges.

Never add captions, stickers, music, transitions, punch-ins, reframing, color grading, voice cleanup, or AI-generated footage. Preserve the source audio and picture. Use only material the user is authorized to download and edit.

## Selection Rules

Prioritize a segment only when it has at least two of the following:

- A strong football opinion, prediction, mockery, or fan-identity statement.
- A clear reversal, payoff, or visible emotional reaction.
- A concise film/TV-dialogue adaptation or character-relationship joke mapped to a player, club, or streamer.
- Enough context for a new viewer to understand the conflict in the first 5–10 seconds.
- A self-contained ending: punchline, replay, reaction, or audience-chat payoff.

Reject filler chat, score updates without a host angle, isolated references that need too much context, and duplicate versions of the same joke.

Target 45–150 seconds per clip. Keep 3–8 seconds before the setup and 3–6 seconds after the payoff. A longer clip is acceptable only if the setup is required to understand the joke.

## Required Output Before Export

Present a compact cut plan:

| ID | In–out | Hook | Why it fits | Proposed filename |
|---|---|---|---|---|

Do not invent exact timestamps. If the source cannot be read, ask for a local recording, transcript, or the user's candidate timestamps.

## Export

Save one JSON file named `cut-plan.json`, then run:

```bash
python3 scripts/rough_cut.py \
  --input /path/to/livestream.mp4 \
  --plan /path/to/cut-plan.json \
  --output /path/to/rough-cuts
```

For a public URL, use `--input-url` only after confirming the user may download it. The script requires `yt-dlp` for URLs and `ffmpeg` for exports.

For transcript-first selection and optional export from a local recording:

```bash
.venv/bin/python skills/video/scripts/transcript_rough_cut.py \
  --input /path/to/livestream.mp4 \
  --transcript-srt /path/to/existing.srt \
  --creator-profile skills/video/profiles/football-100-telan.json \
  --output /path/to/rough-cuts \
  --max-clips 5 --export
```

For a public replay that should be downloaded and delivered at 720p, run:

```bash
.venv/bin/python skills/video/scripts/transcript_rough_cut.py \
  --input-url 'https://www.bilibili.com/video/BV号/' \
  --output /path/to/rough-cuts \
  --download-height 720 \
  --analysis-window-seconds 3600 \
  --creator-profile skills/video/profiles/football-100-telan.json \
  --max-clips 3 --export
```

The URL workflow requests the best available 720p-or-lower source. Exports retain the source frame dimensions and audio, so a downloaded 720p source yields 720p final clips. Do not upscale an older 360p source; download it again at 720p instead.

Use this plan shape:

```json
{
  "title": "英阿赛后直播",
  "clips": [
    {
      "id": "01",
      "start": "00:42:10",
      "end": "00:43:28",
      "hook": "嘴硬预测被进球反转",
      "reason": "有鲜明立场、反转和主播反应"
    }
  ]
}
```

The script defaults to stream-copy export for speed. Use `--reencode` only when the user needs cuts to land exactly on timestamps; that is still a rough cut, not fine editing.

## Handoff

Return the output directory, exported filenames, and the cut plan. State that the clips are intentionally unpolished and ready for review or import into 剪映.
