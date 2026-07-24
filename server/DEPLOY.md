# 오디오 처리 서버 배포 (Cloud Run)

유튜브/업로드 음원에서 원곡·MR(보컬 제거)·키 변경 mp3를 만드는 서버입니다.

## 사전 조건

1. Firebase 프로젝트(lyric-d92bb)를 **Blaze 요금제**로 전환 (Cloud Run/Cloud Build에 결제 필요)
2. gcloud CLI 로그인: `gcloud auth login` → `gcloud config set project lyric-d92bb`

## 배포

저장소 루트에서:

```bash
gcloud run deploy lyric-audio \
  --source server \
  --region asia-northeast3 \
  --project lyric-d92bb \
  --allow-unauthenticated \
  --memory 8Gi --cpu 4 \
  --timeout 3600 \
  --no-cpu-throttling \
  --min-instances 0 --max-instances 2
```

- 인증은 앱 레벨에서 Firebase ID 토큰으로 검증하므로 `--allow-unauthenticated`가 필요합니다.
- `--no-cpu-throttling`: 응답 후에도 백그라운드 스레드가 분리 작업을 계속하도록 CPU를 유지합니다.
- 배포가 끝나면 출력되는 서비스 URL(https://lyric-audio-....run.app)을
  `index.html`의 `AUDIO_SERVER` 상수에 넣고 재배포합니다.

## 비용 감각

- 유휴 시 인스턴스 0 → 기본 요금 없음 (단, no-cpu-throttling은 요청 처리 중에만 과금)
- 곡 1개 처리 ≈ CPU 4코어 × 3~6분 → 회당 수십 원 수준
