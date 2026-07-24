# -*- coding: utf-8 -*-
"""유튜브/업로드 음원 → 원곡 + MR(보컬 제거) + 키 변경 처리 서버 (Cloud Run).

클라이언트는 Firebase ID 토큰으로 인증하고, 진행 상황은
Firestore users/{uid}/jobs/{jobId} 문서로 전달한다.
결과 mp3는 Storage users/{uid}/jobs/{jobId}/ 아래에 올린다.
"""
import os
import subprocess
import tempfile
import threading
import uuid

from flask import Flask, jsonify, request

import firebase_admin
from firebase_admin import auth, firestore
from firebase_admin import storage as fb_storage

firebase_admin.initialize_app(options={
    'storageBucket': os.environ.get('BUCKET', 'lyric-d92bb.firebasestorage.app'),
})
db = firestore.client()
app = Flask(__name__)


def set_status(uid, jid, **kw):
    kw['updatedAt'] = firestore.SERVER_TIMESTAMP
    db.document(f'users/{uid}/jobs/{jid}').set(kw, merge=True)


def process(uid, jid, url, src_path, keys):
    try:
        bucket = fb_storage.bucket()
        with tempfile.TemporaryDirectory() as td:
            title = '음원'
            if url:
                set_status(uid, jid, status='downloading', step='유튜브에서 내려받는 중…')
                subprocess.run(
                    ['yt-dlp', '--no-playlist', '-f', 'bestaudio',
                     '-o', os.path.join(td, 'src.%(ext)s'), url],
                    check=True, timeout=600)
                srcf = next(os.path.join(td, f) for f in os.listdir(td) if f.startswith('src.'))
                got = subprocess.run(
                    ['yt-dlp', '--no-playlist', '--print', '%(title)s', url],
                    capture_output=True, text=True, timeout=120)
                title = (got.stdout.strip().splitlines() or ['음원'])[0][:60] or '음원'
            else:
                set_status(uid, jid, status='downloading', step='업로드한 파일 가져오는 중…')
                srcf = os.path.join(td, 'src.bin')
                bucket.blob(src_path).download_to_filename(srcf)
                title = '업로드 음원'

            wav = os.path.join(td, 'src.wav')
            subprocess.run(['ffmpeg', '-y', '-i', srcf, '-ac', '2', '-ar', '44100', wav],
                           check=True, timeout=600)

            set_status(uid, jid, status='separating', title=title,
                       step='AI 보컬 분리 중… (곡 길이에 따라 몇 분 걸립니다)')
            subprocess.run(
                ['python', '-m', 'demucs', '--two-stems', 'vocals', '-n', 'htdemucs',
                 '-o', os.path.join(td, 'sep'), wav],
                check=True, timeout=3000)
            nv = os.path.join(td, 'sep', 'htdemucs', 'src', 'no_vocals.wav')

            set_status(uid, jid, status='encoding', step='키 변환·인코딩 중…')
            outs = {}

            def enc(name, inp, semi=None):
                out = os.path.join(td, name + '.mp3')
                af = ['-af', f'rubberband=pitch={2 ** (semi / 12.0):.8f}'] if semi else []
                subprocess.run(['ffmpeg', '-y', '-i', inp, *af, '-b:a', '192k', out],
                               check=True, timeout=1200)
                blob = bucket.blob(f'users/{uid}/jobs/{jid}/{name}.mp3')
                blob.upload_from_filename(out, content_type='audio/mpeg')
                outs[name] = blob.name

            enc('원곡', wav)
            enc('MR원키', nv)
            for k in keys:
                if k:
                    enc(f'MR{k:+d}키', nv, k)

            set_status(uid, jid, status='done', step='완료', files=outs, title=title)
    except subprocess.TimeoutExpired:
        set_status(uid, jid, status='error', step='처리 시간 초과 — 다시 시도해 주세요')
    except subprocess.CalledProcessError as e:
        cmd = (e.cmd[0] if isinstance(e.cmd, list) else str(e.cmd))
        hint = '유튜브 다운로드 실패 — 파일 업로드로 시도해 보세요' if cmd == 'yt-dlp' else f'{cmd} 처리 실패'
        set_status(uid, jid, status='error', step=hint)
    except Exception as e:  # noqa: BLE001
        set_status(uid, jid, status='error', step=f'실패: {type(e).__name__}: {str(e)[:200]}')


@app.route('/jobs', methods=['POST'])
def create_job():
    try:
        tok = request.headers.get('Authorization', '').replace('Bearer ', '')
        uid = auth.verify_id_token(tok)['uid']
    except Exception:  # noqa: BLE001
        return jsonify({'error': 'unauthorized'}), 401
    d = request.get_json(force=True, silent=True) or {}
    url = (d.get('url') or '').strip() or None
    src = (d.get('storagePath') or '').strip() or None
    if src and not src.startswith(f'users/{uid}/'):
        return jsonify({'error': 'bad path'}), 400
    if not url and not src:
        return jsonify({'error': 'url or storagePath required'}), 400
    try:
        keys = [int(k) for k in (d.get('keys') or []) if -12 <= int(k) <= 12]
    except (TypeError, ValueError):
        keys = []
    jid = uuid.uuid4().hex[:12]
    set_status(uid, jid, status='queued', step='대기 중…', createdAt=firestore.SERVER_TIMESTAMP)
    threading.Thread(target=process, args=(uid, jid, url, src, keys), daemon=True).start()
    return jsonify({'jobId': jid})


@app.route('/jobs', methods=['OPTIONS'])
def options():
    return ('', 204)


@app.after_request
def cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Authorization,Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'POST,OPTIONS'
    return resp
