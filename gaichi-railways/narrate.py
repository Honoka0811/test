# -*- coding: utf-8 -*-
"""シーンごとのナレーション(男性寄りの声)を Open JTalk で合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
使い方: python3 narrate.py [入力mp4] [出力mp4]
必要: numpy, pyopenjtalk
"""
import sys, os, wave, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'gaichi_railways.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'gaichi_railways_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')

SR = 48000
TOTAL = 102
LEAD = 0.45  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応
# 読み上げ用: 数字は漢数字、Open JTalk が誤読する地名・路線名はカタカナ
SCRIPT = [
    (0, 8.5, '戦前の日本には、内地とは別に、外地と呼ばれた地域がありました。そこを走った鉄道を、地図でたどります。'),
    (8.5, 11.5, '外地とは、台湾、樺太、関東州、朝鮮、そして南洋群島。日清戦争から第一次大戦にかけて、日本の統治下に入った地域です。'),
    (20, 14.5, '台湾では、千九百八年に、基隆と高雄を結ぶ縦貫線が全通。軌間は内地と同じ、千六十七ミリです。東部の台東線やアリサン森林鉄道は、さらに狭い七百六十二ミリでした。'),
    (34.5, 15, '朝鮮の鉄道は、内地より広い標準軌。千八百九十九年のケイジン線に始まり、ケイフ線とケイギ線で半島を縦断します。下関からのカンプ連絡船と結ばれ、大陸への玄関口になりました。'),
    (49.5, 15.5, '日露戦争でロシアから得た鉄道をもとに、南満洲鉄道、満鉄が生まれます。関東州のダイレンから新京への本線と、朝鮮へつながるアンポウ線。千九百三十四年には、特急あじあ号が走りました。'),
    (65, 13.5, '北緯五十度より南の樺太には、樺太庁鉄道が敷かれました。稚内からのチハク連絡船で内地と結ばれ、東海岸線、西海岸線、そして山を越えるホウシン線が走りました。'),
    (78.5, 7.5, '南洋群島では、サイパンやテニアンで、製糖会社がサトウキビを運ぶ軽便鉄道を走らせていました。'),
    (86, 12.5, '台湾と樺太は、内地と同じ狭軌。朝鮮と満洲は、大陸と直通できる標準軌。外地の鉄道は、東京から大陸、そしてヨーロッパへと続く道でもありました。'),
]

# 字幕用テキスト(画面表示向けの表記)
SUBTITLES = [
    '戦前の日本には、内地とは別に「外地」と呼ばれた地域がありました。そこを走った鉄道を、地図でたどります。',
    '外地とは、台湾、樺太、関東州、朝鮮、そして南洋群島。日清戦争から第一次大戦にかけて、日本の統治下に入った地域です。',
    '台湾では、1908年に基隆と高雄を結ぶ縦貫線が全通。軌間は内地と同じ1067mmです。東部の台東線や阿里山森林鉄道は、さらに狭い762mmでした。',
    '朝鮮の鉄道は、内地より広い標準軌。1899年の京仁線に始まり、京釜線と京義線で半島を縦断します。下関からの関釜連絡船と結ばれ、大陸への玄関口になりました。',
    '日露戦争でロシアから得た鉄道をもとに、南満洲鉄道(満鉄)が生まれます。関東州の大連から新京への本線と、朝鮮へつながる安奉線。1934年には特急「あじあ」号が走りました。',
    '北緯50度より南の樺太には、樺太庁鉄道が敷かれました。稚内からの稚泊連絡船で内地と結ばれ、東海岸線、西海岸線、そして山を越える豊真線が走りました。',
    '南洋群島では、サイパンやテニアンで、製糖会社がサトウキビを運ぶ軽便鉄道を走らせていました。',
    '台湾と樺太は内地と同じ狭軌、朝鮮と満洲は大陸と直通できる標準軌。外地の鉄道は、東京から大陸、そしてヨーロッパへと続く道でもありました。',
]
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')

import pyopenjtalk
def engine(text, speed):
    x, sr = pyopenjtalk.tts(text, speed=speed, half_tone=-1.5)
    return x.astype(np.float32) / 32768.0, sr

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def synth(text, speed):
    x, sr = engine(text, speed)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for li, (start, dur, text) in enumerate(SCRIPT):
    limit = dur - LEAD - 0.35
    speed = 1.2  # 基準速度(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.3)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
    # フェードイン/アウト
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR)
    e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append((start + LEAD, start + LEAD + n / SR, SUBTITLES[li]))

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.85
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
print('wrote', WAV)

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
with open(SRT, 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(cues, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{t}\n\n')
print('wrote', SRT)

# ---------- BGM をダッキングしながらミックス ----------
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL)
music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
# ナレーションの包絡(50ms RMS → アタック速く・リリース 0.5 秒で平滑化)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    prev = envl[i - 1] if i else 0.0
    envl[i] = max(v, prev * 0.9)       # リリース ≈ 0.5 秒
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.40, 0.18   # 無音時 / 発話時の BGM ゲイン(線形)
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
# ゲイン変化を 100ms で滑らかに
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(HERE, 'output', 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())
print('wrote', MIX)

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
