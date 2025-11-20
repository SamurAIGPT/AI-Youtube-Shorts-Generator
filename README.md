# AI Youtube Shorts Generator

AI Youtube Shorts Generator is a Python tool designed to generate engaging YouTube shorts from long-form videos. By leveraging the power of GPT-4 and Whisper, it extracts the most interesting highlights, detects speakers, and crops the content vertically for shorts.

![longshorts](https://github.com/user-attachments/assets/3f5d1abf-bf3b-475f-8abf-5e253003453a)

## Features

- **Video Download**: Downloads videos directly from YouTube.
- **Transcription**: Uses Faster-Whisper for accurate speech-to-text transcription.
- **Highlight Extraction**: Utilizes OpenAI's GPT-4 to identify the most engaging parts of the video.
- **Speaker Detection**: Detects active speakers to keep them in frame using OpenCV and DNN models.
- **Vertical Cropping**: Automatically crops the highlighted sections to a 9:16 aspect ratio, perfect for YouTube Shorts, TikTok, and Instagram Reels.

## Installation

### Prerequisites

- **Python 3.8 or higher**: Ensure you have a compatible Python version installed.
- **FFmpeg**: This tool requires FFmpeg for video processing.
  - **Windows**: Download and install from [ffmpeg.org](https://ffmpeg.org/download.html), and add it to your system PATH.
  - **macOS**: Install via Homebrew: `brew install ffmpeg`
  - **Linux**: Install via apt: `sudo apt install ffmpeg`

### Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator.git
   cd AI-Youtube-Shorts-Generator
   ```

2. **Create and activate a virtual environment:**

   On macOS/Linux:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   On Windows:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the environment variables:**

   Create a `.env` file in the project root directory and add your OpenAI API key:

   ```env
   OPENAI_API=your_openai_api_key_here
   ```

## Usage

1. Activate your virtual environment (if not already active).
2. Run the main script:

   ```bash
   python main.py
   ```

3. Enter the YouTube video URL when prompted.

### Output

The script will process the video and generate the following files in the root directory:

- `Out.mp4`: The extracted highlight clip (original aspect ratio).
- `croped.mp4`: The vertically cropped video stream (silent).
- `Final.mp4`: The final result: vertically cropped video with audio, ready for upload.

## Troubleshooting

- **FFmpeg Error**: If you encounter errors related to FFmpeg (e.g., `FileNotFoundError`), ensure FFmpeg is installed and added to your system's PATH.
- **OpenAI API Error**: Ensure your API key is valid and has access to GPT-4 models.
- **OpenCV Error**: If you see errors related to `cv2.imshow` in a headless environment, note that this tool is designed to run in a desktop environment with a display.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.

## Disclaimer

This tool is in beta (v0.1) and may contain bugs. Please report any issues on the [GitHub Repository](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator).

If you wish to add shorts generation into your application, here is an API to create shorts from long-form videos: [Vadoo.tv API](https://docs.vadoo.tv/docs/guide/create-ai-clips)

---

### Other useful Video AI Projects

[AI Influencer generator](https://github.com/SamurAIGPT/AI-Influencer-Generator)

[Text to Video AI](https://github.com/SamurAIGPT/Text-To-Video-AI)

[Faceless Video Generator](https://github.com/SamurAIGPT/Faceless-Video-Generator)

[AI B-roll generator](https://github.com/Anil-matcha/AI-B-roll)

[No-code AI Youtube Shorts Generator](https://www.vadoo.tv/clip-youtube-video)

[Sora AI Video Generator](https://www.vadoo.tv/sora-ai-video-generator)
