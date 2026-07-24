FROM python:3.11-slim

# ffmpeg(Debian 빌드는 rubberband 필터 포함)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# demucs 모델 가중치를 이미지에 미리 내려받아 콜드스타트 단축
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

COPY main.py .
ENV PORT=8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
