# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX: 四国めたん)を合成し、ナレーションの長さに合わせたシーン尺(timing.json)と字幕(SRT)を書き出す。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT    libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS   *.vvm を置いたディレクトリ(0.vvm に四国めたんが含まれる)
  VOICEVOX_DICT   Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE  スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま, 6 = ツンツン, 4 = セクシー)
  NARR_SPEED      話速(既定 1.25)
  NARR_PAUSE      句読点の間の倍率(既定 0.65)
出力: output/narration.wav, output/timing.json, output/subtitles_ja.srt
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('NARR_SPEED', '1.25'))
PAUSE = float(os.environ.get('NARR_PAUSE', '0.65'))
LEAD, TAIL = 0.40, 0.45           # シーン開始→発話開始 / 発話終了→シーン終了 の間
INTRO_TAIL, OUTRO_TAIL = 0.30, 2.4

# (シーンID, 読み上げ原稿, 画面用字幕)
SCRIPT = [
    ('intro', '四十代のうちにやっておくべきこと、十選！',
              '40代のうちにやっておくべきこと10選！'),
    ('s1', '一つ目、毎年の健康診断。体の変化が出やすい年代。人間ドックで早めにチェック。',
           '①毎年の健康診断。体の変化が出やすい年代。人間ドックで早めにチェック。'),
    ('s2', '二つ目、運動習慣。筋肉は四十代から減ります。週二回の筋トレか、毎日の散歩を。',
           '②運動習慣。筋肉は40代から減ります。週2回の筋トレか、毎日の散歩を。'),
    ('s3', '三つ目、歯のメンテナンス。歯を失う原因の一位は歯周病。三か月に一度の検診を。',
           '③歯のメンテナンス。歯を失う原因の1位は歯周病。3か月に1度の検診を。'),
    ('s4', '四つ目、睡眠と食事。七時間睡眠と腹八分目。無理なダイエットより、続く習慣を。',
           '④睡眠と食事。7時間睡眠と腹八分目。無理なダイエットより、続く習慣を。'),
    ('s5', '五つ目、老後資金の計画。新ニーサやイデコで、まずは月一万円から始めましょう。',
           '⑤老後資金の計画。新NISAやiDeCoで、まずは月1万円から始めましょう。'),
    ('s6', '六つ目、学び直し。資格や語学、エーアイ。新しいスキルが、五十代の選択肢を広げます。',
           '⑥学び直し。資格や語学、AI。新しいスキルが、50代の選択肢を広げます。'),
    ('s7', '七つ目、親と話しておく。介護やお金のこと、元気なうちに聞いておきましょう。',
           '⑦親と話しておく。介護やお金のこと、元気なうちに聞いておきましょう。'),
    ('s8', '八つ目、人間関係の整理。気を使うだけの付き合いは手放して、心地いい人を大切に。',
           '⑧人間関係の整理。気を使うだけの付き合いは手放して、心地いい人を大切に。'),
    ('s9', '九つ目、やりたかったことに挑戦。旅行でも楽器でも、体力があるうちに。',
           '⑨やりたかったことに挑戦。旅行でも楽器でも、体力があるうちに。'),
    ('s10', '十個目、持ち物と保険の見直し。使わないものは手放して、身軽な五十代へ。',
            '⑩持ち物と保険の見直し。使わないものは手放して、身軽な50代へ。'),
    ('outro', '全部やらなくて大丈夫。まずは一つ、今日から始めてみてくださいね。',
              '全部やらなくて大丈夫。まずは1つ、今日から始めてみてくださいね。'),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort_path = os.environ.get('VOICEVOX_ORT') or glob.glob('/home/user/vv/ort/**/libvoicevox_onnxruntime.so', recursive=True)[0]
ort = Onnxruntime.load_once(filename=ort_path)
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
name = next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == STYLE)
print('engine: VOICEVOX', name, 'speed', SPEED)

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15   # 少し抑揚を強めて明るく
    for ap in q.accent_phrases:          # 句読点の間(pause_mora)を詰めてテンポよく
        if ap.pause_mora is not None:
            ap.pause_mora['vowel_length'] = ap.pause_mora['vowel_length'] * PAUSE
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.08
    wav = synth.synthesis(q, STYLE)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1000): idx[-1] + 2400]
    f = min(500, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips = [(sid, tts(text), sub) for sid, text, sub in SCRIPT]

timing, t = [], 0.0
for sid, x, sub in clips:
    sec = len(x) / SR
    tail = INTRO_TAIL if sid == 'intro' else OUTRO_TAIL if sid == 'outro' else TAIL
    dur = round(LEAD + sec + tail, 2)
    timing.append({'id': sid, 'start': round(t, 2), 'dur': dur, 'nstart': round(t + LEAD, 2), 'nend': round(t + LEAD + sec, 2), 'subtitle': sub})
    print(f'{sid:6s} start={t:5.2f}s  voice={sec:4.2f}s  scene={dur:4.2f}s')
    t += dur
TOTAL = round(t, 2)
print('TOTAL', TOTAL, 's')

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for (sid, x, sub), ti in zip(clips, timing):
    s = int(ti['nstart'] * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

json.dump({'total': TOTAL, 'speaker': name, 'scenes': timing}, open(os.path.join(OUT, 'timing.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def _ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, ti in enumerate(timing, 1):
        f.write(f"{i}\n{_ts(ti['nstart'])} --> {_ts(min(ti['nend'] + 0.3, TOTAL))}\n{ti['subtitle']}\n\n")
print('wrote output/narration.wav, output/timing.json, output/subtitles_ja.srt')
