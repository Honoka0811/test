# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を文ごとに合成し、実際の音声長からシーン尺・字幕タイミングを決める。
出力: output/narration.wav, output/timings.json(.js), output/subtitles_ja.srt
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.15       # 話速
LEAD = 0.5         # シーン開始 → 最初の発話
GAP = 0.22         # 文と文の間
TAIL = 0.7         # 最後の発話 → 次のシーン
END_HOLD = 2.2     # 最終シーンの余韻

# シーンごとの (読み上げ用, 字幕表示用) の文リスト。字幕の '|' は改行位置の指定。render.html の SCENES と順番が対応
SCRIPT = [
    [('みなさん、ごきげんよう。四国めたんですわ。', 'みなさん、ごきげんよう。四国めたんですわ。'),
     ('今日は、世界を変えた物理学の大発見を、五つ紹介しますわね。', '今日は、世界を変えた物理学の大発見を、5つ紹介しますわね。')],
    [('一つ目は、ニュートンの万有引力。', '1つ目は、ニュートンの万有引力。'),
     ('リンゴが落ちるのも、月が地球を回るのも、同じ法則だと見抜いたのです。', 'リンゴが落ちるのも、月が地球を回るのも、同じ法則だと見抜いたのです。'),
     ('この法則が、人工衛星やロケットの軌道計算を支えていますわ。', 'この法則が、人工衛星や|ロケットの軌道計算を支えていますわ。')],
    [('二つ目は、ファラデーの電磁誘導。', '2つ目は、ファラデーの電磁誘導。'),
     ('磁石を動かすと、コイルに電気が流れる。', '磁石を動かすと、コイルに電気が流れる。'),
     ('この発見から発電機とモーターが生まれ、電気の時代が始まりました。', 'この発見から発電機とモーターが生まれ、電気の時代が始まりました。')],
    [('三つ目は、マクスウェルの電磁波。', '3つ目は、マクスウェルの電磁波。'),
     ('電気と磁気の波が、光と同じ速さで空間を伝わると予言しました。', '電気と磁気の波が、光と同じ速さで空間を伝わると予言しました。'),
     ('ラジオもスマホもワイファイも、この波のおかげですわ。', 'ラジオもスマホもWi-Fiも、この波のおかげですわ。')],
    [('四つ目は、アインシュタインの相対性理論。', '4つ目は、アインシュタインの相対性理論。'),
     ('時間と空間は、速さや重力で伸び縮みする。', '時間と空間は、速さや重力で伸び縮みする。'),
     ('ジーピーエスは、このずれを補正しないと、一日に十キロ以上も狂ってしまうのです。', 'GPSは、このずれを補正しないと、1日に10km以上も狂ってしまうのです。')],
    [('五つ目は、量子力学。', '5つ目は、量子力学。'),
     ('ミクロの世界では、電子は粒であり、波でもある。', 'ミクロの世界では、電子は粒であり、波でもある。'),
     ('この不思議な理論から半導体が生まれ、コンピューターの時代が開かれました。', 'この不思議な理論から半導体が生まれ、コンピューターの時代が開かれました。')],
    [('世界は、たった一つの発見で変わる。', '世界は、たった1つの発見で変わる。'),
     ('次の大発見をするのは、あなたかもしれませんわね。', '次の大発見をするのは、あなたかもしれませんわね。')],
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return pyopenjtalk.OPEN_JTALK_DICT_DIR.decode() if isinstance(pyopenjtalk.OPEN_JTALK_DICT_DIR, bytes) else pyopenjtalk.OPEN_JTALK_DICT_DIR

def make_engine():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
        '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
    synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
        with VoiceModelFile.open(f) as m:
            synth.load_voice_model(m)
    style = int(os.environ.get('VOICEVOX_STYLE', '2'))
    name = next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == style)
    print('engine: VOICEVOX', name)
    def tts(text):
        q = synth.create_audio_query(text, style)
        q.speed_scale = SPEED
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(synth.synthesis(q, style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx): x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
        f = min(600, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x
    return tts

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}'

if __name__ == '__main__':
    tts = make_engine()
    clips, scenes, cues = [], [], []
    t = 0.0
    for si, sents in enumerate(SCRIPT):
        start = t; t += LEAD
        for read, disp in sents:
            x = tts(read)
            clips.append((t, x)); cues.append({'s': round(t, 3), 'e': round(t + len(x) / SR, 3), 'text': disp, 'scene': si})
            t += len(x) / SR + GAP
        t += TAIL - GAP + (END_HOLD if si == len(SCRIPT) - 1 else 0)
        scenes.append({'start': round(start, 3), 'dur': round(t - start, 3)})
        print(f'scene {si}: {start:5.2f}s +{t - start:5.2f}s')
    total = round(t, 2)
    track = np.zeros(int(total * SR) + 1, dtype=np.float32)
    for s, x in clips:
        i = int(s * SR); track[i:i + len(x)] += x[:len(track) - i]
    track = track / (np.max(np.abs(track)) or 1) * 0.85
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    data = {'total': total, 'scenes': scenes, 'cues': cues}
    json.dump(data, open(os.path.join(OUT, 'timings.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'timings.js'), 'w', encoding='utf-8') as f:  # render.html が読む
        f.write('window.TIMINGS = ' + json.dumps(data, ensure_ascii=False) + ';\n')
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{_ts(c['s'])} --> {_ts(c['e'] + 0.15)}\n{c['text'].replace('|', '')}\n\n")
    print('total', total, 's')
