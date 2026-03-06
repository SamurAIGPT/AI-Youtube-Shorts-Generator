# HF Spaces compatible – GPU optional, CPU fallback works too
FROM python:3.10-slim

# System deps
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    libgl1 \
    libglib2.0-0 \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick security policy for subtitle rendering
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' \
    /etc/ImageMagick-6/policy.xml 2>/dev/null || true

# Non-root user required by HF Spaces
RUN useradd -m -u 1000 appuser
WORKDIR /home/appuser/app
RUN chown appuser:appuser /home/appuser/app

USER appuser

# Install Python deps
COPY --chown=appuser:appuser requirements-cpu.txt requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements-cpu.txt && \
    pip install --user --no-cache-dir gradio

ENV PATH="/home/appuser/.local/bin:$PATH"

# Copy project
COPY --chown=appuser:appuser . .

# HF Spaces expects port 7860
EXPOSE 7860

CMD ["python", "app.py"]
