FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libfreetype6 \
    libgl1 libglx-mesa0 libgl1-mesa-dri libegl1 libglu1-mesa \
    libx11-6 libxext6 libxrandr2 libxcursor1 libxi6 libxxf86vm1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Synthesize all audio once (cached unless the sound code changes), outside /app so dev mounts keep it.
COPY malchorya/sound malchorya/sound
COPY tools/make_audio.py tools/make_audio.py
ENV MALCHORYA_AUDIO_DIR=/opt/malchorya_audio
RUN python3 tools/make_audio.py /opt/malchorya_audio

COPY . .

ENV PYTHONPATH=/app/malchorya
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python3", "malchorya/main.py"]
