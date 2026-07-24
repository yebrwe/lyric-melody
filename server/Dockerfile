FROM python:3.11-slim

# ffmpeg(Debian 빌드는 rubberband 필터 포함) + git/curl
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 — POT 프로바이더 서버 + yt-dlp EJS 런타임용
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# demucs 모델 가중치를 이미지에 미리 내려받아 콜드스타트 단축
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

# 유튜브 봇 차단 우회용 PO 토큰 프로바이더 서버 (기본 포트 4416)
RUN git clone --single-branch --branch 1.3.1 --depth 1 \
        https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/pot \
    && cd /opt/pot/server && npm ci && npx tsc && npm cache clean --force

COPY main.py start.sh ./
RUN chmod +x start.sh
ENV PORT=8080
CMD ["./start.sh"]
