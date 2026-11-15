# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)をシーンごとに合成し、各シーンの尺をナレーション長から決める。
出力: output/narration.wav, output/timeline.json(render.html が読む), output/subtitles_ja.srt
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = 1.25
LEAD, TAIL = 0.25, 0.35   # シーン頭の間 / 読み終わりからシーン切替までの間

# (読み上げ原稿, 字幕表記)
SCRIPT = [
    ('北海道大学のここがすごい！じゅっせん！',
     '北海道大学のここがすごい！10選！'),
    ('ひとつめ。札幌駅から歩いて、たったの七分。',
     '①札幌駅から歩いて、たったの7分。'),
    ('ふたつめ。キャンパスは、東京ドーム三十八個分。移動は自転車が必須ですわ。',
     '②キャンパスは東京ドーム38個分。移動は自転車が必須ですわ。'),
    ('みっつめ。研究林を含めた総面積は、東京二十三区より広いんですの。',
     '③研究林を含めた総面積は、東京23区より広いんですの。'),
    ('よっつめ。札幌農学校として千八百七十六年に誕生。今年で百五十周年ですわ。',
     '④札幌農学校として1876年に誕生。今年で150周年ですわ。'),
    ('いつつめ。少年よ大志を抱け。クラーク博士は、初代教頭ですの。',
     '⑤「少年よ大志を抱け」のクラーク博士は初代教頭ですの。'),
    ('むっつめ。旧五千円札の顔、新渡戸稲造も卒業生ですわ。',
     '⑥旧5千円札の顔、新渡戸稲造も卒業生ですわ。'),
    ('ななつめ。鈴木章名誉教授が、ノーベル化学賞を受賞。',
     '⑦鈴木章 名誉教授がノーベル化学賞を受賞。'),
    ('やっつめ。総合入試なら、入学後に学部を選べますわ。',
     '⑧総合入試なら、入学後に学部を選べますわ。'),
    ('ここのつめ。秋は、金色に輝くイチョウ並木。',
     '⑨秋は金色に輝くイチョウ並木。'),
    ('とおめ。総合博物館は、なんと入場無料ですの。',
     '⑩総合博物館は、なんと入場無料ですの。'),
    ('行ってみたくなったら、いいねとフォロー、お願いしますわ！',
     '行ってみたくなったら、いいねとフォローお願いしますわ！'),
]


def load_engine():
    import pyopenjtalk
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
        '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
    dic = os.environ.get('VOICEVOX_DICT') or pyopenjtalk.OPEN_JTALK_DICT_DIR.decode()
    synth = Synthesizer(ort, OpenJtalk(dic))
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
        with VoiceModelFile.open(f) as m:
            synth.load_voice_model(m)
    style = int(os.environ.get('VOICEVOX_STYLE', '2'))
    print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == style))

    def say(text):
        q = synth.create_audio_query(text, style)
        q.speed_scale = SPEED
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(synth.synthesis(q, style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        return x[max(0, idx[0] - 1200): idx[-1] + 2400] if len(idx) else x
    return say


def main():
    say = load_engine()
    clips, scenes, t = [], [], 0.0
    for i, (yomi, sub) in enumerate(SCRIPT):
        x = say(yomi)
        n = len(x); f = min(600, n // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        dur = LEAD + n / SR + TAIL
        if i == len(SCRIPT) - 1:
            dur += 1.0  # 最後は少し余韻
        scenes.append({'start': round(t, 3), 'dur': round(dur, 3),
                       'voiceStart': round(t + LEAD, 3), 'voiceEnd': round(t + LEAD + n / SR, 3), 'sub': sub})
        clips.append((t + LEAD, x))
        print(f'{i:2d} {t:6.2f}s  len={n / SR:4.2f}s  {sub[:20]}…')
        t += dur
    total = round(t, 3)
    track = np.zeros(int(total * SR) + 1, dtype=np.float32)
    for s, x in clips:
        a = int(s * SR); track[a:a + len(x)] += x[:len(track) - a]
    track = track / (np.max(np.abs(track)) or 1) * 0.85
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump({'total': total, 'scenes': scenes}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:  # file:// でも読めるように
        f.write('window.TL = ' + json.dumps({'total': total, 'scenes': scenes}, ensure_ascii=False) + ';\n')

    def ts(v):
        return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, s in enumerate(scenes, 1):
            f.write(f"{i}\n{ts(s['voiceStart'])} --> {ts(min(s['voiceEnd'] + 0.3, total))}\n{s['sub']}\n\n")
    print('total', total, 's')


if __name__ == '__main__':
    main()
