# -*- coding: utf-8 -*-
"""シーンごとのナレーション(男性音声)を Open JTalk で合成し、動画に合成する。
使い方: python3 narrate.py [入力mp4] [出力mp4]
必要: pip install pyopenjtalk numpy / ffmpeg
"""
import sys, os, wave, subprocess
import numpy as np
import pyopenjtalk

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'pacific_war_power_gap.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'pacific_war_power_gap_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')

SR = 48000
TOTAL = 60.0
LEAD = 0.45  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応
SCRIPT = [
    (0.0, 4.5, '太平洋戦争。日米の戦力差はどう変わったのか。'),
    (4.5, 7.5, '開戦時の国力。GDPは米国が約五点六倍、鉄鋼は約十一倍、石油は約五百四十倍。'),
    (12.0, 7.5, 'しかし空母は日本十隻に対し、米国は太平洋に三隻。この優位が緒戦の快進撃を支えました。'),
    (19.5, 10.5, '航空機の生産数。千九百四十三年、米国は年間八万六千機を生産し、差は決定的に。累計は日本七万機、米国三十一万機でした。'),
    (30.0, 10.5, '空母の保有数。ミッドウェーの損失を日本は埋められず、四十三年に米国が逆転。四十五年には日本の稼働空母はほぼゼロに。'),
    (40.5, 8.5, '日本の商船は潜水艦の攻撃で六百四十万トンから百五十万トンへ激減。石油も枯渇し、艦隊は動けなくなります。'),
    (49.0, 6.5, '量の差は質の差へ。搭乗員の飛行時間は百時間未満に落ち、マリアナ沖では約三百機を失いました。'),
    (55.5, 4.5, '緒戦の優位は、国力の差を覆せませんでした。'),
]

def synth(text, speed):
    x, sr = pyopenjtalk.tts(text, speed=speed, half_tone=-1.5)  # やや低めの男性声
    assert sr == SR
    x = x.astype(np.float32) / 32768.0
    # 前後の無音を詰める
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
for start, dur, text in SCRIPT:
    limit = dur - LEAD - 0.35
    speed = 1.25  # 基準速度(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.45)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
    # フェードイン/アウト
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR)
    e = min(s + n, len(track))
    track[s:e] += x[:e - s]

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.85
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
print('wrote', WAV)

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', WAV,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
