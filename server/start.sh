#!/bin/sh
# POT 프로바이더를 백그라운드로 띄운 뒤 API 서버 시작
node /opt/pot/server/build/main.js --port 4416 &
exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
