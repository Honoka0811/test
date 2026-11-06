# -*- coding: utf-8 -*-
"""script.py の原稿を VOICEVOX(四国めたん)で 1 文ずつ合成し、タイムライン(timing.json)・ナレーション音声・SRT を書き出す。
合成は WEB版 VOICEVOX API(tts.quest v3, 低速API・APIキー不要)を使う。結果は cache/ に保存して再実行時は再利用する。
使い方: python3 narrate.py
環境変数: VOICEVOX_SPEAKER (既定 2 = 四国めたん ノーマル)
"""
import os, sys, json, time, wave, hashlib, subprocess, urllib.parse
import numpy as np
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache'); OUT = os.path.join(HERE, 'output')
os.makedirs(CACHE, exist_ok=True); os.makedirs(OUT, exist_ok=True)
SPEAKER = int(os.environ.get('VOICEVOX_SPEAKER', '2'))
API = 'https://api.tts.quest/v3/voicevox/synthesis'
SR = 48000

LEAD = 0.7      # シーン開始から最初の文まで
GAP = 0.45      # 文と文の間
TAIL = 1.3      # 最後の文からシーン終了まで
TITLE_LEAD = 1.4  # タイトルシーンだけ少し長めに

def curl(url, out=None, timeout=90):
    cmd = ['curl', '-sS', '--max-time', str(timeout), url]
    if out: cmd += ['-o', out]
    r = subprocess.run(cmd, capture_output=True, text=(out is None))
    if r.returncode != 0:
        raise RuntimeError(f'curl failed: {r.stderr}')
    return r.stdout

def synth(text):
    key = hashlib.sha1(f'{SPEAKER}|{text}'.encode()).hexdigest()[:16]
    path = os.path.join(CACHE, f'{key}.wav')
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    for attempt in range(8):
        q = urllib.parse.urlencode({'text': text, 'speaker': SPEAKER})
        res = json.loads(curl(f'{API}?{q}'))
        if not res.get('success'):
            wait = float(res.get('retryAfter', 5)) + 1
            print(f'  rejected ({res.get("errorMessage", res)}); retry in {wait:.0f}s', flush=True)
            time.sleep(wait); continue
        for _ in range(40):
            st = json.loads(curl(res['audioStatusUrl']))
            if st.get('isAudioError'):
                raise RuntimeError(f'audio error for: {text}')
            if st.get('isAudioReady'):
                break
            time.sleep(1.5)
        curl(res['wavDownloadUrl'], out=path)
        if os.path.getsize(path) > 1000:
            time.sleep(1.0)  # 連続リクエストを避ける
            return path
    raise RuntimeError('synthesis failed: ' + text)

def load(path):
    with wave.open(path) as w:
        sr = w.getframerate(); ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    # 前後の無音を詰める
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx): x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    f = min(480, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips = []  # (scene_idx, line_idx, audio)
total_lines = sum(len(s['lines']) for s in SCENES)
k = 0
for si, s in enumerate(SCENES):
    for li, line in enumerate(s['lines']):
        k += 1
        p = synth(line)
        x = load(p)
        clips.append((si, li, x))
        print(f'[{k:2d}/{total_lines}] {len(x)/SR:5.2f}s  {line[:30]}', flush=True)

# ---- タイムライン ----
timeline = []  # scenes
t = 0.0
ci = 0
for si, s in enumerate(SCENES):
    start = t
    t += TITLE_LEAD if s['id'] == 'title' else LEAD
    lines = []
    for li, line in enumerate(s['lines']):
        _, _, x = clips[ci]; ci += 1
        d = len(x) / SR
        lines.append(dict(text=line, start=round(t, 3), end=round(t + d, 3)))
        t += d + GAP
    t += TAIL - GAP
    timeline.append(dict(id=s['id'], start=round(start, 3), end=round(t, 3), lines=lines))
TOTAL = round(t + 0.5, 2)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
ci = 0
for sc in timeline:
    for ln in sc['lines']:
        _, _, x = clips[ci]; ci += 1
        s0 = int(ln['start'] * SR); track[s0:s0 + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(OUT, 'timing.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(total=TOTAL, fps=30, scenes=timeline), f, ensure_ascii=False, indent=1)

def ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    n = 0
    for sc in timeline:
        for ln in sc['lines']:
            n += 1
            f.write(f"{n}\n{ts(ln['start'])} --> {ts(ln['end'] + 0.3)}\n{ln['text']}\n\n")
print(f'total {TOTAL:.1f}s  ({TOTAL/60:.1f} min)')
for sc in timeline:
    print(f"  {sc['id']:10s} {sc['start']:6.1f} - {sc['end']:6.1f}")
