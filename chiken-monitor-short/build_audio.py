# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を文ごとに合成し、タイムライン(timeline.js)と字幕(SRT)を書き出す。
さらに BGM(bgm.py)をダッキングしながらミックスして output/mix.wav を作る。
使い方: python3 build_audio.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  0.vvm を置いたディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)

SR = 48000
SPEED = 1.26        # 話速
LEAD = 0.35         # 冒頭の間
GAP = 0.18          # 文と文の間
SCENE_GAP = 0.45    # シーンの切り替わりの間
TAIL = 1.6          # 最後のカードを見せる時間

# シーンごとの原稿。(字幕の表記, 読み上げ用の表記。None なら字幕と同じ)
SCRIPT = [
    [('寝ているだけで高収入？', None),
     ('治験モニターの本当のところを、四国めたんが解説するわ。', None)],
    [('治験とは、新しい薬が国の承認を受けるための臨床試験。', None),
     ('その効き目や安全性を確かめるのに協力するのが、治験モニターよ。', None)],
    [('実はこれ、アルバイトではなくボランティア。', None),
     ('受け取るお金は給料ではなく、「負担軽減費」と呼ばれるの。', '受け取るお金は給料ではなく、負担軽減費と呼ばれるの。')],
    [('参加の流れはこう。', None),
     ('説明を受けて、納得したら同意書にサイン。', None),
     ('健康診断に通ったら、入院や通院で、薬の服用や採血などの検査を受けるわ。', '健康診断に通ったら、入院や通院で、薬の服用や、採血などの検査を受けるわ。')],
    [('負担軽減費は、通院なら1回7千円から1万円ほどが目安。', '負担軽減費は、通院なら一回、七千円から一万円ほどが目安。'),
     ('入院タイプは、まとまった金額になることも。', None)],
    [('ただし注意点も。', None),
     ('副作用のリスクはゼロではないし、お酒やタバコも制限されるわ。', None),
     ('参加後、3〜4か月ほどは次の治験に参加できないの。', '参加後、三か月から四か月ほどは、次の治験に参加できないの。')],
    [('でも安心して。', None),
     ('治験は国のルールで厳しく審査されているし、', None),
     ('参加をやめるのは、いつでも自由よ。', None)],
    [('未来の薬づくりを支える、治験モニター。', None),
     ('説明をよく聞いて、納得してから参加してね。', None)],
]


def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d:
        return d
    import pyopenjtalk
    pyopenjtalk.g2p('あ')  # 初回は辞書をダウンロードする
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')


def load_engine():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    ort = Onnxruntime.load_once(filename=os.environ.get(
        'VOICEVOX_ORT', '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
    synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
        with VoiceModelFile.open(f) as m:
            synth.load_voice_model(m)
    style = int(os.environ.get('VOICEVOX_STYLE', '2'))
    name = next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == style)
    print('engine: VOICEVOX', name)
    return synth, style


def resample(x, sr):
    if sr == SR:
        return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def write_wav(path, x, ch=1):
    with wave.open(path, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', path)


def main():
    synth, style = load_engine()

    def say(text):
        q = synth.create_audio_query(text, style)
        q.speed_scale = SPEED
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.03
        q.post_phoneme_length = 0.05
        print('   ', q.kana)
        wav = synth.synthesis(q, style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        x = resample(x, sr)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx):
            x = x[max(0, idx[0] - 600): idx[-1] + 1800]
        f = min(300, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x

    t = LEAD
    pieces, scenes = [], []
    for si, lines in enumerate(SCRIPT):
        scene_start = 0.0 if si == 0 else t - SCENE_GAP / 2
        cues = []
        for disp, read in lines:
            x = say(read or disp)
            pieces.append((t, x))
            cues.append({'start': round(t, 3), 'end': round(t + len(x) / SR, 3), 'text': disp})
            t += len(x) / SR + GAP
        t += SCENE_GAP - GAP
        scenes.append({'start': round(scene_start, 3), 'cues': cues})
    total = round(t - SCENE_GAP + TAIL, 2)
    for i, s in enumerate(scenes):
        s['end'] = scenes[i + 1]['start'] if i + 1 < len(scenes) else total

    voice = np.zeros(int(total * SR), dtype=np.float32)
    for start, x in pieces:
        s = int(start * SR)
        voice[s:s + len(x)] += x
    voice = voice / (np.max(np.abs(voice)) or 1) * 0.85
    write_wav(os.path.join(OUT, 'narration.wav'), voice)

    with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('window.TIMELINE = ' + json.dumps({'total': total, 'scenes': scenes}, ensure_ascii=False, indent=1) + ';\n')
    print('wrote timeline.js  total =', total)

    def ts(v):
        ms = int(round(v * 1000))
        return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        n = 0
        for s in scenes:
            for c in s['cues']:
                n += 1
                f.write(f"{n}\n{ts(c['start'])} --> {ts(c['end'] + 0.15)}\n{c['text']}\n\n")

    # ---------- BGM をダッキングしながらミックス(ステレオ) ----------
    import bgm
    music = bgm.generate(total)                       # (n, 2)
    write_wav(os.path.join(OUT, 'bgm.wav'), music.reshape(-1), ch=2)
    n = len(voice)
    music = music[:n] if len(music) >= n else np.pad(music, ((0, n - len(music)), (0, 0)))
    hop = SR // 20
    rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(rms)
    for i, v in enumerate(rms):
        env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
    env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
    speech = np.clip(env / 0.1, 0, 1)
    gain = 0.50 - (0.50 - 0.20) * speech               # 無音時 / 発話時の BGM ゲイン
    k = SR // 8
    gain = np.convolve(gain, np.ones(k) / k, mode='same')
    mixed = voice[:, None] + music * gain[:, None]
    mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
    write_wav(os.path.join(OUT, 'mix.wav'), mixed.reshape(-1), ch=2)


if __name__ == '__main__':
    main()
