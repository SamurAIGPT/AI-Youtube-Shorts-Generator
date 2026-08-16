# Creator Style Video Clipper

Creator Style Video Clipper is a local, transcript-first workflow for rough-cutting a creator's long videos and livestreams.

Most automatic clipping tools look for generic “viral moments.” This project takes a different approach: it learns from the creator's own confirmed high-performing videos, saves the observed style as a readable JSON profile, and uses that profile to select complete discussion topics from a new video. The result is a reviewable rough-cut plan with timestamps and reasons for every selected segment.

The project is designed for creators, editors, and researchers working with content they own or are authorized to process.

## Highlights

- Build a reusable creator profile from supplied high-performing videos.
- Process public video sites supported by `yt-dlp`, or a local media file.
- Run download, transcription, ranking, and export locally.
- Select complete topic blocks instead of forcing arbitrary 45–120 second clips.
- Analyze a long recording in hourly windows without cutting a topic at an hour boundary.
- Save editor feedback in `clip-feedback.json` and use it in later runs.
- Generate a cut plan before exporting; MP4 export is opt-in.
- Preserve the original frame and source audio in exported rough cuts.
- Require no OpenAI, Gemini, or other hosted-model API key.

## How the workflow works

```text
Confirmed high-performing videos
        ↓
Local Whisper transcripts
        ↓
Readable creator profile (JSON)
        ↓
Target video download / local input
        ↓
Timestamped target transcript
        ↓
Hourly candidate analysis + complete-topic boundaries
        ↓
Profile-aware ranking + editor feedback
        ↓
candidate-cut-plan.json
        ↓  (only when --export is supplied)
Original-frame, original-audio MP4 rough cuts
```

## Requirements

- Python 3.10 or newer and `ffmpeg` available in your terminal.
- A public video URL supported by `yt-dlp`, or a local media file.
- Enough disk space for source video, Whisper model files, transcripts, and optional exports.

Install the Python dependencies in a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Confirm that `ffmpeg` is available before running an export:

```bash
ffmpeg -version
```

On macOS, install it with Homebrew if needed:

```bash
brew install ffmpeg
```

`faster-whisper` may download a local Whisper model the first time it transcribes a video. After that, cached model files can be reused. This is a local model download, not a paid model API call.

## Quick start

Give the workflow two or more confirmed high-performing videos from the same creator, plus the target long video or livestream replay:

```bash
python main.py video-workflow "TARGET_VIDEO_URL" \
  --creator "Creator name" \
  --history-url "HIGH_PERFORMING_VIDEO_URL_1" \
  --history-url "HIGH_PERFORMING_VIDEO_URL_2" \
  --output output/my-run
```

This creates the profile, transcript, hourly analysis, cut plan, and feedback template. Review `candidate-cut-plan.json` before exporting.

When the plan is acceptable, run again with `--export`:

```bash
python main.py video-workflow "TARGET_VIDEO_URL" \
  --creator "Creator name" \
  --history-url "HIGH_PERFORMING_VIDEO_URL_1" \
  --history-url "HIGH_PERFORMING_VIDEO_URL_2" \
  --output output/my-run \
  --export --reencode
```

`--reencode` is slower but produces more accurate timestamps. Without it, export uses stream-copy cutting when possible.

## A complete first-run walkthrough

The first run is deliberately split into review and export. This prevents the tool from turning every automatically selected candidate into a video file before an editor has checked the context.

### 1. Choose representative examples

Select two to four historical videos that you have already judged as successful for this creator. They should represent the kind of moments you want the workflow to find again: for example, strong opinions, storytelling, reactions, tutorials, recurring jokes, or interview answers. Do not mix unrelated formats or another creator's videos into the same profile.

### 2. Create a draft cut plan

```bash
python main.py video-workflow "https://example.com/target-video" \
  --creator "Example Creator" \
  --history-url "https://example.com/high-performing-video-1" \
  --history-url "https://example.com/high-performing-video-2" \
  --output output/example-creator-episode-01 \
  --max-clips 6
```

The workflow downloads the authorized source material, transcribes it locally, writes a `creator-profile.json`, and then creates `candidate-cut-plan.json`. At this point it has **not** exported MP4 files.

### 3. Review the proposed clips

Open `output/example-creator-episode-01/candidate-cut-plan.json`. Each entry contains:

```json
{
  "id": "01",
  "start": "00:12:40",
  "end": "00:14:03",
  "hook": "The opening transcript line for the candidate",
  "reason": "topic/person, creator stance, reaction/reversal, complete topic block",
  "context": "Nearby transcript text used for the ranking"
}
```

Verify the start includes the setup, the end contains the conclusion, and the chosen moment actually represents the creator's style. If a topic is still in progress for longer than the supported rough-cut length, the workflow favors leaving it out over exporting a fragment.

### 4. Record editorial feedback

Open the generated `clip-feedback.json`. Its `feedback` array is a review record for the current candidates; `preferences` controls later ranking. A practical edited version can look like this:

```json
{
  "creator": "Example Creator",
  "instructions": "Keep complete topics and prioritize clear personal takes.",
  "preferences": {
    "boost_keywords": ["my conclusion", "unexpected result"],
    "suppress_keywords": ["routine announcement"]
  },
  "feedback": [
    {
      "clip_id": "01",
      "decision": "keep",
      "reason": "Includes the full setup and payoff.",
      "keywords": ["unexpected result"],
      "suggested_start": "00:12:40",
      "suggested_end": "00:14:03"
    },
    {
      "clip_id": "02",
      "decision": "adjust",
      "reason": "Start ten seconds earlier to include the question.",
      "keywords": [],
      "suggested_start": "00:22:10",
      "suggested_end": "00:23:04"
    }
  ]
}
```

`keep`, `reject`, and `adjust` document the editor's decision. The current implementation applies `boost_keywords` and `suppress_keywords` directly to the next ranking; the per-clip decisions and suggested timestamps are retained as human editorial notes for review.

### 5. Run the next episode with the saved profile and feedback

```bash
python main.py video-workflow "https://example.com/next-target-video" \
  --creator "Example Creator" \
  --creator-profile output/example-creator-episode-01/creator-profile.json \
  --clip-feedback output/example-creator-episode-01/clip-feedback.json \
  --output output/example-creator-episode-02 \
  --max-clips 6
```

This skips historical-video analysis. Candidates matching a preferred keyword are boosted and identify that preference in their reason; candidates matching a suppressed keyword are filtered out.

### 6. Export approved rough cuts

After reviewing the plan for a run, rerun that command with `--export --reencode`. The exported MP4 files are written to `OUTPUT_DIRECTORY/exports/`.

## Inputs

### Target video

The first positional argument can be:

- A public video or livestream replay URL that `yt-dlp` can download.
- An absolute or relative path to a local video file.

Some videos cannot be downloaded automatically: login-only, paid, DRM-protected, region-restricted, or anti-bot-protected videos may require browser cookies or may be unavailable to the downloader.

### Historical high-performing videos

Use `--history-url` once for each verified high-performing video. These are the source material for the creator profile. Three to four representative examples generally provide a better profile than a single example.

For an offline run, use existing subtitle files instead:

```bash
python main.py video-workflow "/path/to/recording.mp4" \
  --creator "Creator name" \
  --history-transcript-srt "/path/to/hit-1.srt" \
  --history-transcript-srt "/path/to/hit-2.srt" \
  --target-transcript-srt "/path/to/recording.srt" \
  --output output/offline-run
```

## Reusing or editing a creator profile

Every initial run creates `creator-profile.json`. It records the observed high-frequency subjects and recurring phrases from the historical transcripts. The selection signals are transparent and can be edited:

```json
{
  "creator": "Creator name",
  "signals": {
    "topic": ["recurring subject or person"],
    "stance": ["characteristic opinion phrase"],
    "payoff": ["reaction, reversal, or conclusion"],
    "adaptation": ["catchphrase or recurring bit"]
  }
}
```

Reuse a saved profile when processing another video from the same creator:

```bash
python main.py video-workflow "TARGET_VIDEO_URL_OR_LOCAL_FILE" \
  --creator "Creator name" \
  --creator-profile /path/to/creator-profile.json \
  --output output/next-run
```

The repository includes a neutral starting example at `skills/video/profiles/example-creator-profile.json`.

### What the profile generator does—and does not do

The generator uses deterministic text analysis of the supplied transcripts. It records recurring Chinese phrases and longer terms, then places them into the `signals` object. It does not infer personality, view counts, visual style, camera work, emotions that are absent from the transcript, or the reasons a video performed well on a platform. Review the generated JSON and add, remove, or clarify terms before relying on it for a long editing series.

## Selection rules

The workflow looks for a combination of:

- Topics and expressions from the creator profile.
- A clear opinion or stance.
- A reaction, result, reversal, or conclusion.
- A recurring catchphrase or recognizable format.

Candidates are bounded by natural pauses in the transcript. The workflow keeps the setup and conclusion together, and will skip an overlong ongoing topic rather than silently cutting it in half. Hourly analysis is only used for discovery; topic boundaries are calculated against the full transcript, so a discussion can continue across an hour boundary.

The selection is transcript-led. It is most reliable for spoken commentary, interviews, explanations, and discussions with clear pauses. It is less reliable when the source has overlapping speakers, long music-only passages, poor audio, missing speech recognition, or no clear break between topics. Treat the output as a rough-cut proposal, not as final editorial judgment.

## Editor feedback

Each run creates `clip-feedback.json`. After review, record whether each proposal should be kept, rejected, or adjusted. You can also save recurring preferences:

```json
{
  "preferences": {
    "boost_keywords": ["phrases to prefer"],
    "suppress_keywords": ["phrases to avoid"]
  }
}
```

Pass the same file to a later run:

```bash
python main.py video-workflow "TARGET_VIDEO_URL" \
  --creator "Creator name" \
  --creator-profile /path/to/creator-profile.json \
  --clip-feedback /path/to/clip-feedback.json \
  --output output/next-run
```

Matching preferred terms receive a ranking boost and are named in the clip reason. Candidates containing suppressed terms are excluded.

## Outputs

All artifacts are written to the directory set by `--output`:

| File or directory | Purpose |
| --- | --- |
| `creator-profile.json` | Creator style extracted from historical samples. |
| `transcript.json` | Timestamped transcript for the target video. |
| `hourly-analysis.json` | Candidate counts and leading candidates for each time window. |
| `candidate-cut-plan.json` | Selected clips, timestamps, hooks, scores, contexts, and reasons. |
| `clip-feedback.json` | Editable editorial decisions and keyword preferences. |
| `exports/*.mp4` | Rough-cut videos, created only with `--export`. |

The cut plan is the main editorial handoff: it shows why each clip was selected before any media is rendered.

## Main command options

| Option | Description |
| --- | --- |
| `--creator` | Required creator or account name. |
| `--history-url` | A confirmed high-performing video URL; repeat for multiple examples. |
| `--history-transcript-srt` | Historical SRT file for offline profile generation; repeatable. |
| `--creator-profile` | Existing profile JSON; skips historical-video analysis. |
| `--target-transcript-srt` | Existing target SRT; skips target transcription. |
| `--clip-feedback` | Existing feedback JSON to apply during ranking. |
| `--max-clips` | Maximum number of regular rough-cut proposals. Default: `5`. |
| `--analysis-window-seconds` | Analysis window length. Default: `3600` seconds. |
| `--candidates-per-window` | Candidate count retained per analysis window. Default: `5`. |
| `--format` | Requested download height. Default: `720`. |
| `--export` | Export selected MP4 rough cuts. |
| `--reencode` | Use slower, timestamp-accurate export. |

`video-workflow` is the single public workflow command for every supported platform.

## Commands for common situations

### Process a local recording with an existing profile

```bash
python main.py video-workflow "/absolute/path/to/recording.mp4" \
  --creator "Example Creator" \
  --creator-profile "/absolute/path/to/creator-profile.json" \
  --output output/local-recording
```

### Use 30-minute review windows instead of the default hour

```bash
python main.py video-workflow "TARGET_VIDEO_URL" \
  --creator "Example Creator" \
  --creator-profile "/absolute/path/to/creator-profile.json" \
  --analysis-window-seconds 1800 \
  --candidates-per-window 8 \
  --output output/half-hour-review
```

### Produce a plan only, with no download/transcription repeat

This still requires the target media file because the plan records its source and can later be exported, but uses the provided SRT files for analysis:

```bash
python main.py video-workflow "/absolute/path/to/recording.mp4" \
  --creator "Example Creator" \
  --creator-profile "/absolute/path/to/creator-profile.json" \
  --target-transcript-srt "/absolute/path/to/recording.srt" \
  --output output/review-only
```

## Project structure

```text
main.py
skills/video/
├── SKILL.md                         # Reusable creator-clipping instructions
├── profiles/
│   └── example-creator-profile.json # Public neutral profile example
└── scripts/
    ├── creator_workflow.py          # End-to-end workflow
    ├── analyze_creator_profile.py   # Profile generation
    ├── transcript_rough_cut.py      # Topic boundaries and ranking
    ├── rough_cut.py                 # MP4 rough-cut export
    └── local/                       # Local downloading and transcription
tests/
└── test_creator_workflow.py         # Offline public workflow tests
```

## Privacy and repository scope

This repository contains the general-purpose workflow. Generated outputs, downloaded media, cached models, and creator-specific profiles are excluded from Git. Private creator extensions can remain local without changing the public workflow.

Only process media you own or have permission to download, transcribe, edit, and distribute. The tool does not remove copyright, platform, privacy, or licensing obligations.

## Troubleshooting

### `ffmpeg` is not found

Install `ffmpeg`, close and reopen the terminal, then confirm `ffmpeg -version` works. It is required for media conversion and MP4 export.

### A video URL does not download

First verify the URL is playable in a normal browser. Some services require login cookies, a membership, a geographic location, or block automated downloads. Try a local source file if you have authorized access to the recording.

### The transcript is incomplete or uses the wrong words

Speech recognition quality depends on the source audio. Use a clearer source, review the generated transcript, or supply a corrected SRT with `--target-transcript-srt`. A corrected historical SRT can likewise be supplied with `--history-transcript-srt` before building the profile.

### The proposed clips start or end at the wrong place

Check the transcript around that timestamp. The workflow follows transcript pauses, so a missing pause or incorrect timestamp can affect a boundary. Record the adjustment in `clip-feedback.json`, improve the SRT if necessary, and rerun. Export only after the plan has been reviewed.

### No clips are selected

The candidate needs enough matching evidence: meaningful topic text plus at least one other signal such as a stance, payoff, or recurring phrase. Review the profile's `signals`, add representative historical samples, expand the relevant signal lists, or use a more accurate transcript.

## Tests

Run the offline public tests with:

```bash
venv/bin/python -m unittest discover -s tests -v
```

They verify profile creation, profile-aware selection, complete-topic boundaries, hourly-boundary handling, editorial feedback, URL/local-file handling, and compatibility aliases.

For the Chinese guide, see [项目说明.md](项目说明.md).
