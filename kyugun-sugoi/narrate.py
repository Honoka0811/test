# -*- coding: utf-8 -*-
"""四国めたん(VOICEVOX)でナレーションを合成し、タイムライン(timeline.json / timeline.js)と字幕(SRT)を書き出す。
映像(render.html)はこのタイムラインに合わせて描画されるので、原稿を書き換えたらこれを最初に実行する。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  0.vvm(四国めたん)を置いたディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.14        # 話速
GAP = 0.16          # 同じシーン内の文と文の間(秒)
SCENE_LEAD = 0.45   # シーン開始から話し始めるまで
SCENE_TAIL = 0.55   # 話し終わってから次のシーンまで

# シーンID(render.html の描画関数と対応)と、(読み上げ用テキスト, 字幕用テキスト) の並び
SCRIPT = [
    ('title', [
        ('旧にほん軍の、ここがすごい!', '旧日本軍の、ここがすごい!'),
        ('いつつ、ご紹介しますわ。', '5つ、ご紹介しますわ。'),
    ]),
    ('zero', [
        ('そのいち、ゼロ戦。', 'その1、零戦。'),
        ('航続距離は、およそ三千キロ。', '航続距離は、およそ3,000km。'),
        ('当時の戦闘機の常識を、大きく超えていましたの。', '当時の戦闘機の常識を、大きく超えていましたの。'),
    ]),
    ('torpedo', [
        ('そのに、酸素魚雷。', 'その2、酸素魚雷。'),
        ('射程は、最大四十キロ。', '射程は、最大40km。'),
        ('しかも、航跡がほとんど見えませんわ。', 'しかも、航跡がほとんど見えませんわ。'),
    ]),
    ('yamato', [
        ('そのさん、戦艦やまと。', 'その3、戦艦大和。'),
        ('四十六センチの主砲は、史上最大。', '46cmの主砲は、史上最大。'),
        ('砲弾一発が、およそ一点五トンもありますの。', '砲弾1発が、およそ1.5トンもありますの。'),
    ]),
    ('kido', [
        ('そのよん、空母機動部隊。', 'その4、空母機動部隊。'),
        ('空母六隻を集中して運用する発想は、世界に先駆けたものでしたわ。', '空母6隻を集中して運用する発想は、世界に先駆けたものでしたわ。'),
    ]),
    ('i400', [
        ('そのご、い、よんひゃくがた潜水艦。', 'その5、伊400型潜水艦。'),
        ('攻撃機を三機積んで、地球を一周半も、航行できましたの。', '攻撃機を3機積んで、地球を1周半も航行できましたの。'),
    ]),
    ('outro', [
        ('ただ、技術は一流でも、国力と補給の差は埋められませんでした。', 'ただ、技術は一流でも、国力と補給の差は埋められませんでした。'),
        ('歴史から学べることは、多いですわね。', '歴史から学べることは、多いですわね。'),
    ]),
]


def make_engine():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    import pyopenjtalk
    dic = os.environ.get('VOICEVOX_DICT') or os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')
    if not os.path.isdir(dic):
        pyopenjtalk.g2p('あ')  # 辞書を自動ダウンロード
    ort_path = os.environ.get('VOICEVOX_ORT') or glob.glob('/home/user/vv/ort/*/lib/libvoicevox_onnxruntime.so')[0]
    synth = Synthesizer(Onnxruntime.load_once(filename=ort_path), OpenJtalk(dic))
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
        with VoiceModelFile.open(f) as m:
            synth.load_voice_model(m)
    style = int(os.environ.get('VOICEVOX_STYLE', '2'))
    name = next((c.name + '/' + st.name) for c in synth.metas() for st in c.styles if st.id == style)
    print('engine: VOICEVOX', name)

    def tts(text):
        q = synth.create_audio_query(text, style)
        q.speed_scale = SPEED
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.03
        q.post_phoneme_length = 0.03
        print('  ', text, '=>', q.kana)
        with wave.open(io.BytesIO(synth.synthesis(q, style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        n = int(len(x) * SR / sr)
        return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return tts


def main():
    os.makedirs(OUT, exist_ok=True)
    tts = make_engine()
    t = 0.0
    clips, scenes = [], []
    for sid, lines in SCRIPT:
        start = t
        t += SCENE_LEAD
        cues = []
        for i, (read, sub) in enumerate(lines):
            x = tts(read)
            d = len(x) / SR
            clips.append((t, x))
            cues.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': sub})
            t += d + (GAP if i < len(lines) - 1 else 0)
        t += SCENE_TAIL
        scenes.append({'id': sid, 'start': round(start, 3), 'end': round(t, 3), 'cues': cues})
    total = round(t + 0.6, 3)   # 最後に少し余韻
    scenes[-1]['end'] = total

    track = np.zeros(int(total * SR), dtype=np.float32)
    for s, x in clips:
        a = int(s * SR)
        track[a:a + len(x)] += x[:len(track) - a]
    track *= 0.9 / np.max(np.abs(track))
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    tl = {'fps': 30, 'duration': total, 'scenes': scenes}
    with open(os.path.join(HERE, 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('window.TIMELINE = ' + json.dumps(tl, ensure_ascii=False) + ';\n')

    def ts(v):
        ms = int(round(v * 1000))
        return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        n = 0
        for sc in scenes:
            for c in sc['cues']:
                n += 1
                f.write(f"{n}\n{ts(c['start'])} --> {ts(c['end'] + 0.1)}\n{c['text']}\n\n")
    print('total %.2fs' % total)
    for sc in scenes:
        print('  %-8s %6.2f - %6.2f' % (sc['id'], sc['start'], sc['end']))


if __name__ == '__main__':
    main()
