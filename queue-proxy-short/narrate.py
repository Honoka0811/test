# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、字幕データと BGM ミックスを書き出す。
出力: output/narration.wav, output/mix.wav(ステレオ), output/subtitles_ja.srt, output/subs.js(render.html が読む字幕)
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
VV = os.environ.get('VOICEVOX_HOME', '/home/user/vv')

SR = 48000
TOTAL = 58.5
LEAD = 0.4  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 読み上げ原稿, 字幕)  render.html の SCENES と対応
SCRIPT = [
    (0, 6, '並ぶだけでお金がもらえる?今日は、行列代行のお仕事を紹介するわね。',
           '並ぶだけでお金がもらえる?今日は、行列代行のお仕事を紹介するわね。'),
    (6, 10, '行列代行とは、依頼者の代わりに行列に並ぶお仕事よ。人気店のスイーツや限定グッズ、イベントの整理券など、並ぶ対象はいろいろ。',
            '行列代行とは、依頼者の代わりに行列に並ぶお仕事よ。人気店のスイーツや限定グッズ、イベントの整理券など、並ぶ対象はいろいろ。'),
    (16, 9.5, '流れはシンプル。依頼を受けて、現地で並んで、順番が来たら依頼者と交代するか、代わりに受け取って渡す。これだけよ。',
              '流れはシンプル。依頼を受けて、現地で並んで、順番が来たら依頼者と交代するか、代わりに受け取って渡す。これだけよ。'),
    (25.5, 8, '報酬は、一時間あたり千円から二千円ほどが目安。早朝や悪天候の日は、割増になることもあるわ。',
              '報酬は、1時間あたり1,000〜2,000円ほどが目安。早朝や悪天候の日は、割増になることもあるわ。'),
    (33.5, 9.5, '待つのが苦にならない人や、時間をきっちり守れる人に向いているわ。ただし、夏の暑さや冬の寒さ、長時間の立ちっぱなしは覚悟してね。',
                '待つのが苦にならない人や、時間をきっちり守れる人に向いているわ。ただし、夏の暑さや冬の寒さ、長時間の立ちっぱなしは覚悟してね。'),
    (43, 8, '注意したいのは、代行での行列を禁止しているお店やイベントもあること。事前にルールを確認するのが鉄則よ。',
            '注意したいのは、代行での行列を禁止しているお店やイベントもあること。事前にルールを確認するのが鉄則よ。'),
    (51, 7.5, '誰かの待ち時間を引き受ける、行列代行。気になったら、まずは近所の募集をチェックしてみてね。',
              '誰かの待ち時間を引き受ける、行列代行。気になったら、まずは近所の募集をチェックしてみてね。'),
]

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth_ = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth_.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth_.metas() for s in c.styles if s.id == STYLE))

def synth(text, speed):
    q = synth_.create_audio_query(text, STYLE)
    q.speed_scale = speed
    q.intonation_scale = 1.15   # 少し抑揚を強めて明るく
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth_.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    return x[max(0, idx[0] - 1200): idx[-1] + 2400] if len(idx) else x

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for start, dur, text, sub in SCRIPT:
    limit = dur - LEAD - 0.4
    speed = 1.15
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit: break
        speed = min(speed * (sec / limit) * 1.02, 1.3)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:16]}…')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR); e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append((start + LEAD, start + LEAD + n / SR, sub))

track = track / (np.max(np.abs(track)) or 1) * 0.85
def write_wav(path, x, ch):
    with wave.open(path, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', path)
write_wav(os.path.join(OUT, 'narration.wav'), track, 1)

# 字幕: SRT と render.html 用 JS
def _ts(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(cues, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{t}\n\n')
with open(os.path.join(OUT, 'subs.js'), 'w', encoding='utf-8') as f:
    f.write('window.SUBS = ' + json.dumps([{'a': round(a, 3), 'b': round(b, 3), 'text': t} for a, b, t in cues],
                                          ensure_ascii=False) + ';\n')
print('wrote subtitles_ja.srt, subs.js')

# BGM をダッキングしながらミックス
music = bgm_mod.generate(TOTAL)
music = np.pad(music, ((0, max(0, len(track) - len(music))), (0, 0)))[:len(track)]
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)   # リリース ≈ 0.5 秒
envl = np.pad(np.repeat(envl, hop), (0, len(track) - len(rms) * hop))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.38, 0.15
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track[:, None] + music * gain[:, None]
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
write_wav(os.path.join(OUT, 'mix.wav'), mixed, 2)
