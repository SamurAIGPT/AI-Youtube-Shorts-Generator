# AI YouTube Shorts Generator

Generate short vertical videos from a YouTube video or a local video file.

The project has three modes:

- `api`: MuAPI handles downloading, transcription, highlight selection, and cropping.
- `local`: downloads, transcribes, and crops locally, but uses OpenAI or Gemini for highlight selection.
- `self`: uses highlight timestamps that you provide and performs downloading and cropping locally. It does not use MuAPI, Whisper, OpenAI, or Gemini.

## Requirements

- Python 3.10 or newer
- FFmpeg and FFprobe
- A virtual environment
- `requirements-local.txt` for `local` or `self` mode

On Windows, install FFmpeg with WinGet if needed:

```powershell
winget install --id Gyan.FFmpeg
```

The project also searches common WinGet locations when FFmpeg is not already on `PATH`.

## Setup on Windows

From `D:\ONGOING PROJECTS\Shorts-generator`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
cd .\AI-Youtube-Shorts-Generator
pip install -r requirements-local.txt
```

Copy `.env.example` to `.env` and fill in only the settings required by your mode.

## Modes

### API mode

Requires `MUAPI_API_KEY` and uses MuAPI for the full workflow:

```powershell
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mode api
```

### Local mode

Uses `yt-dlp`, `faster-whisper`, FFmpeg, and OpenCV locally. Highlight selection still calls the provider selected by `LLM_PROVIDER`.

```powershell
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mode local
python main.py "D:\Videos\input.mp4" --mode local
```

Set either `GEMINI_API_KEY` with `LLM_PROVIDER=gemini`, or `OPENAI_API_KEY` with `LLM_PROVIDER=openai`.

### Self mode: provide your own moments

Use this mode when you already know the best moments or when the LLM quota is exhausted. It does not call MuAPI or any LLM. FFmpeg and OpenCV create the clips locally.

Create `highlight.json`:

```json
[
  {
    "start_time": 30,
    "end_time": 55,
    "title": "Opening hook",
    "score": 100,
    "hook_sentence": "The strongest opening moment"
  },
  {
    "start_time": 180,
    "end_time": 225,
    "title": "Main point",
    "score": 95,
    "hook_sentence": "The key moment"
  }
]
```

Run it with a local file:

```powershell
python main.py "D:\Videos\input.mp4" --mode self --self-highlights highlight.json --aspect-ratio 9:16
```

You can also use a YouTube URL. `yt-dlp` downloads the source locally first, then FFmpeg crops it locally:

```powershell
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mode self --self-highlights highlight.json --aspect-ratio 9:16
```

The accepted time keys are `start_time`/`end_time`; `start`/`end` are also accepted. `title`, `score`, and `hook_sentence` are optional.

## Output

Local and self modes write files to `output/` by default:

```text
output/
├── short_01.mp4
├── short_02.mp4
└── ...
```

Change the destination with `LOCAL_OUTPUT_DIR` in `.env`. Use `--output-json result.json` to save run metadata and generated clip paths:

```powershell
python main.py "D:\Videos\input.mp4" --mode self --self-highlights highlight.json --output-json result.json
```

The output uses the requested aspect ratio, with `9:16` as the default. Local cropping uses OpenCV face tracking when a face is detected and FFmpeg for encoding and audio.

## Configuration

`.env.example` contains the available settings:

```dotenv
# Required only for --mode api
MUAPI_API_KEY=

# Required only for --mode local
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# Local processing
LOCAL_WHISPER_MODEL=base
LOCAL_WHISPER_DEVICE=auto
LOCAL_OUTPUT_DIR=output
```

`--mode self` needs no API keys and does not use the Whisper settings.

## Command options

```text
--mode              api, local, or self
--num-clips         Number of clips to render; default: 3
--aspect-ratio      Output ratio; default: 9:16
--format            YouTube download height; default: 720
--language          Whisper language for local mode
--self-highlights   JSON text or a path to a JSON file; required for self mode
--output-json       Save result metadata as JSON
```

## Project layout

```text
main.py                         CLI entry point
shorts_generator/pipeline.py    Mode dispatcher
shorts_generator/local/         Local downloader, Whisper, LLM, and clipper
shorts_generator/clipper.py     MuAPI cropping for api mode
output/                         Downloaded sources and rendered clips
```

## Troubleshooting

### Whisper produced no segments
The video may have no detectable speech, or it may be in a language Whisper struggles with. Try passing `--language en` (or the correct ISO-639-1 code) to skip auto-detection.

### Looking for better results?
The [AI Clipping API](https://muapi.ai/playground/ai-clipping?utm_source=github&utm_medium=readme&utm_campaign=ai-youtube-shorts-generator) uses an improved algorithm that produces higher-quality clips with better highlight detection.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.

## Related Projects

- [AI Influencer Generator](https://github.com/SamurAIGPT/AI-Influencer-Generator)
- [Text to Video AI](https://github.com/SamurAIGPT/Text-To-Video-AI)
- [Faceless Video Generator](https://github.com/SamurAIGPT/Faceless-Video-Generator)
- [AI B-roll Generator](https://github.com/Anil-matcha/AI-B-roll)
- [No-code YouTube Shorts Generator](https://www.vadoo.tv/clip-youtube-video)
