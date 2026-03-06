import gradio as gr
import os
import uuid
import re
import tempfile
import shutil

# ── Pipeline helpers ────────────────────────────────────────────────
from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight
from Components.FaceCrop import crop_to_vertical, combine_videos
from Components.Subtitles import add_subtitles_to_video


def clean_filename(title: str) -> str:
    cleaned = title.lower()
    cleaned = re.sub(r'[<>:"/\\|?*\[\]]', '', cleaned)
    cleaned = re.sub(r'[\s_]+', '-', cleaned)
    cleaned = re.sub(r'-+', '-', cleaned)
    return cleaned.strip('-')[:80]


def generate_short(youtube_url: str, video_file, openai_key: str, progress=gr.Progress()):
    """Main pipeline function called by Gradio."""

    # ── Validate inputs ──────────────────────────────────────────────
    if not openai_key.strip():
        raise gr.Error("Please enter your OpenAI API key.")
    if not youtube_url.strip() and video_file is None:
        raise gr.Error("Provide a YouTube URL or upload a video file.")

    # Inject the key so LanguageTasks picks it up
    os.environ["OPENAI_API"] = openai_key.strip()

    session_id = str(uuid.uuid4())[:8]
    work_dir = tempfile.mkdtemp(prefix=f"shorts_{session_id}_")

    try:
        # ── Step 1 – Obtain source video ─────────────────────────────
        progress(0.05, desc="Getting source video…")

        if video_file is not None:
            Vid = video_file
            video_title = os.path.splitext(os.path.basename(Vid))[0]
        else:
            Vid = download_youtube_video(youtube_url.strip())
            if not Vid:
                raise gr.Error("Failed to download the YouTube video. Check the URL and try again.")
            Vid = Vid.replace(".webm", ".mp4")
            video_title = os.path.splitext(os.path.basename(Vid))[0]

        # ── Step 2 – Extract audio ───────────────────────────────────
        progress(0.15, desc="Extracting audio…")
        audio_file = os.path.join(work_dir, f"audio_{session_id}.wav")
        Audio = extractAudio(Vid, audio_file)
        if not Audio:
            raise gr.Error("Could not extract audio from the video.")

        # ── Step 3 – Transcribe ──────────────────────────────────────
        progress(0.30, desc="Transcribing audio (this may take a while)…")
        transcriptions = transcribeAudio(Audio)
        if not transcriptions:
            raise gr.Error("No speech detected in the video.")

        TransText = "\n".join(f"{s} - {e}: {t}" for t, s, e in transcriptions)

        # ── Step 4 – Find best highlight ─────────────────────────────
        progress(0.55, desc="Selecting best highlight with AI…")
        start, stop = GetHighlight(TransText)
        if start is None or stop is None:
            raise gr.Error("AI failed to select a highlight. Check your OpenAI API key and try again.")

        if not (start >= 0 and stop > start):
            raise gr.Error(f"Invalid highlight times: {start}s – {stop}s")

        # ── Step 5 – Build the short ─────────────────────────────────
        temp_clip      = os.path.join(work_dir, f"clip_{session_id}.mp4")
        temp_cropped   = os.path.join(work_dir, f"cropped_{session_id}.mp4")
        temp_subtitled = os.path.join(work_dir, f"subtitled_{session_id}.mp4")
        clean_title    = clean_filename(video_title) if video_title else "output"
        final_output   = os.path.join(work_dir, f"{clean_title}_{session_id}_short.mp4")

        progress(0.65, desc="Cutting clip…")
        crop_video(Vid, temp_clip, start, stop)

        progress(0.75, desc="Cropping to 9:16 vertical…")
        crop_to_vertical(temp_clip, temp_cropped)

        progress(0.85, desc="Adding subtitles…")
        add_subtitles_to_video(temp_cropped, temp_subtitled, transcriptions, video_start_time=start)

        progress(0.95, desc="Merging audio & video…")
        combine_videos(temp_clip, temp_subtitled, final_output)

        progress(1.0, desc="Done!")

        if not os.path.exists(final_output):
            raise gr.Error("Output file was not created. Check logs for errors.")

        info = (
            f"**Highlight:** {start}s – {stop}s  ({stop - start}s duration)\n\n"
            f"**Transcription segments:** {len(transcriptions)}"
        )
        return final_output, info

    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(f"Unexpected error: {e}")


# ── Gradio UI ────────────────────────────────────────────────────────
with gr.Blocks(
    title="AI YouTube Shorts Generator",
    theme=gr.themes.Soft(),
    css=".output-video{max-height:520px}",
) as demo:
    gr.Markdown(
        """
# 🎬 AI YouTube Shorts Generator
Automatically find the best highlight in any video and turn it into a **9:16 short** with subtitles.

> **Needs an OpenAI API key** (used for highlight selection via GPT-4o-mini).
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            openai_key = gr.Textbox(
                label="OpenAI API Key",
                placeholder="sk-…",
                type="password",
            )
            youtube_url = gr.Textbox(
                label="YouTube URL",
                placeholder="https://www.youtube.com/watch?v=…",
            )
            gr.Markdown("**— or —**")
            video_file = gr.Video(label="Upload a video file")
            run_btn = gr.Button("Generate Short ▶", variant="primary")

        with gr.Column(scale=1):
            output_video = gr.Video(label="Generated Short", elem_classes="output-video")
            output_info  = gr.Markdown()

    run_btn.click(
        fn=generate_short,
        inputs=[youtube_url, video_file, openai_key],
        outputs=[output_video, output_info],
    )

    gr.Markdown(
        """
---
**Tips**
- Processing a 10-min video takes ~2–4 minutes (transcription + AI + rendering).
- YouTube downloads require a public, non-age-restricted video.
- Set your OpenAI key once per session; it is never stored.
        """
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
