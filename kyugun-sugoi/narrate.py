# -*- coding: utf-8 -*-
"""青山龍星(VOICEVOX)でナレーションを合成し、タイムライン(timeline.json / timeline.js)と字幕(SRT)を書き出す。
映像(render.html)と効果音(mix.py)はこのタイムラインに合わせて作られるので、原稿を書き換えたらこれを最初に実行する。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  15.vvm(青山龍星)を置いたディレクトリ
  VOICEVOX_STYLE スタイルID(既定 13 = 青山龍星 ノーマル)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.32        # 話速(ショート向けにやや速め)
GAP = 0.12          # 同じシーン内の文と文の間(秒)
SCENE_TAIL = 0.22   # 話し終わってから次のシーンまで

# シーン: (ID, 話し始めまでの間, 行の並び)
# 行: (読み上げ用テキスト, 字幕(/ で改行), 字幕で強調する語, 効果音タグ)
#   効果音タグ: boom=重い衝撃音 / rank=順位の打ち込み / pop=数字が出る音 / fire=砲撃 / hit=被弾 / ping=ソナー / none
SCRIPT = [
    ('hook', 0.12, [
        ('八十年前の日本は、世界が驚く兵器を作っていた。', '80年前の日本は、/世界が驚く兵器を作っていた。', '世界が驚く兵器', 'boom'),
        ('旧にほん軍の、すごい技術ランキング。', '旧日本軍の すごい技術ランキング', 'ランキング', 'boom'),
        ('一位は、他の国には作れなかった。', '1位は、/他の国には作れなかった。', '作れなかった', 'pop'),
    ]),
    ('zero', 0.2, [
        ('第五位、ゼロ戦。', '第5位 零戦', '零戦', 'rank'),
        ('航続距離は、三千キロ。', '航続距離は、約3,000km。', '3,000km', 'pop'),
        ('東京から、フィリピンまで飛べる。', '東京から/フィリピンまで飛べる。', 'フィリピン', 'none'),
        ('アメリカの戦闘機の、三倍近い。', 'アメリカの戦闘機の3倍近い。', '3倍', 'boom'),
    ]),
    ('kido', 0.2, [
        ('第四位、空母機動部隊。', '第4位 空母機動部隊', '空母機動部隊', 'rank'),
        ('空母六隻を、ひとつの艦隊にまとめた。', '空母6隻を、/1つの艦隊にまとめた。', '6隻', 'pop'),
        ('三百五十機の攻撃隊が、真珠湾へ向かった。', '350機の攻撃隊が、/真珠湾へ向かった。', '350機', 'boom'),
    ]),
    ('i400', 0.2, [
        ('第三位、い、よんひゃくがた潜水艦。', '第3位 伊400型潜水艦', '伊400型', 'rank'),
        ('潜水艦なのに、攻撃機を三機も積んでいた。', '潜水艦なのに、/攻撃機を3機も積んでいた。', '攻撃機を3機', 'pop'),
        ('しかも補給なしで、地球を一周半。', 'しかも補給なしで、/地球を1周半。', '地球を1周半', 'ping'),
    ]),
    ('yamato', 0.2, [
        ('第二位、戦艦やまと。', '第2位 戦艦大和', '戦艦大和', 'rank'),
        ('主砲は、史上最大の四十六センチ。', '主砲は、史上最大の46cm。', '46cm', 'pop'),
        ('砲弾一発が、一点五トン。乗用車一台ぶんだ。', '砲弾1発が1.5トン。/乗用車1台分だ。', '1.5トン', 'fire'),
    ]),
    ('torpedo', 0.9, [   # 1位の前は少し溜める(BGM も止める)
        ('第一位、酸素魚雷。', '第1位 酸素魚雷', '酸素魚雷', 'rank'),
        ('射程は、アメリカの魚雷の、およそ三倍。', '射程は、/アメリカの魚雷のおよそ3倍。', '3倍', 'pop'),
        ('しかも、/泡の跡がほとんど見えない。', 'しかも、/泡の跡がほとんど見えない。', '見えない', 'none'),
        ('敵は、どこから撃たれたのかさえ、分からなかった。', '敵は、どこから撃たれたのか/さえ分からなかった。', 'どこから撃たれたのか', 'hit'),
    ]),
    ('outro', 0.3, [
        ('これほどの技術があっても、/日本は負けた。', 'これほどの技術があっても、/日本は負けた。', '日本は負けた', 'boom'),
        ('なぜなのか。答えは、数字にある。', 'なぜなのか。/答えは「数字」にある。', '数字', 'pop'),
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
    style = int(os.environ.get('VOICEVOX_STYLE', '13'))
    name = next((c.name + '/' + st.name) for c in synth.metas() for st in c.styles if st.id == style)
    print('engine: VOICEVOX', name)

    def tts(text, rank=False):
        q = synth.create_audio_query(text, style)
        q.speed_scale = SPEED * (0.92 if rank else 1.0)   # 順位の読み上げは少し溜めて言う
        q.intonation_scale = 1.25
        q.pitch_scale = 0.0
        q.volume_scale = 1.1 if rank else 1.0
        q.pre_phoneme_length = 0.02
        q.post_phoneme_length = 0.02
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
    for sid, lead, lines in SCRIPT:
        start = t
        t += lead
        cues = []
        for i, (read, sub, hl, sfx) in enumerate(lines):
            x = tts(read, rank=(sfx == 'rank'))
            d = len(x) / SR
            clips.append((t, x))
            cues.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': sub, 'hl': hl, 'sfx': sfx})
            t += d + (GAP if i < len(lines) - 1 else 0)
            if sfx == 'rank':
                t += 0.2   # 順位のあとに一拍おく
        t += SCENE_TAIL
        scenes.append({'id': sid, 'start': round(start, 3), 'end': round(t, 3), 'cues': cues})
    total = round(t + 1.4, 3)   # 最後のカードを少し見せる
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
                f.write(f"{n}\n{ts(c['start'])} --> {ts(c['end'] + 0.1)}\n{c['text'].replace('/', chr(10))}\n\n")
    print('total %.2fs' % total)
    for sc in scenes:
        print('  %-8s %6.2f - %6.2f' % (sc['id'], sc['start'], sc['end']))


if __name__ == '__main__':
    main()
