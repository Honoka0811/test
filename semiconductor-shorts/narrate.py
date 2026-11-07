# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、実際の音声長からシーン尺とフレーズ単位の字幕タイミングを決める。
出力: output/narration.wav / output/timeline.json / output/timeline.js(render.html 用)/ output/subtitles_ja.srt
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス(既定 vendor/ort/*/lib/...)
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(0.vvm に四国めたんが入っている)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル / 0 あまあま / 6 ツンツン / 4 セクシー)
  NARRATION_SPEED 話速(既定 1.2)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
VENDOR = os.environ.get('VOICEVOX_HOME', os.path.join(HERE, 'vendor'))
os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('NARRATION_SPEED', '1.2'))

# シーンごとに (読み上げ, 画面字幕) のフレーズを並べる。
# 読み上げ側の句読点(、。?)ごとに区切りの間が入るので、そこを字幕の切り替え点に使う。
# 画面字幕の [ ] で囲んだ部分は強調色で表示される。
SCRIPT = [
    ('hook', 0.45, 0.45, [
        ('ただの砂が、', 'ただの[砂]が'),
        ('年間100兆円に化ける。', '年間[100兆円]に化ける'),
        ('それが、半導体産業よ。', 'それが[半導体]産業'),
    ]),
    ('purity', 0.3, 0.4, [
        ('原料は、ただの砂。', '原料は ただの砂'),
        ('これを9が11個並ぶ純度まで、', '[9が11個]並ぶ純度まで'),
        ('精製するの。', '精製する'),
    ]),
    ('nano', 0.3, 0.4, [
        ('最先端は、2ナノ世代。', '最先端は[2ナノ]世代'),
        ('ナノは10億分の1メートル。', 'ナノ＝[10億分の1]m'),
        ('髪の毛の、4万分の1よ。', '髪の毛の[4万分の1]'),
    ]),
    ('tr', 0.3, 0.4, [
        ('手のひらサイズのチップに、', '手のひらサイズのチップに'),
        ('トランジスタが2000億個。', 'トランジスタ[2,000億個]'),
        ('工程は1000以上、', '工程は[1,000以上]'),
        ('完成まで3か月かかるわ。', '完成まで[3か月]'),
    ]),
    ('tsmc', 0.3, 0.45, [
        ('でも、最先端チップの9割は、', '最先端チップの[9割]は'),
        ('台湾のティーエスエムシー、', '台湾の[TSMC]'),
        ('たった1社が作ってる。', '[たった1社]が製造'),
        ('台湾が止まれば、', '台湾が止まれば'),
        ('スマホも、車も、AIも止まるのよ。', 'スマホも車もAIも[止まる]'),
    ]),
    ('asml', 0.3, 0.4, [
        ('しかも、工場に欠かせない露光装置を、', '工場に欠かせない[露光装置]'),
        ('作れるのは、オランダのエーエスエムエル1社だけ。', '作れるのは[ASML] 1社だけ'),
        ('1台、数百億円よ。', '1台[数百億円]'),
    ]),
    ('japan', 0.3, 0.4, [
        ('じゃあ、日本は?', 'じゃあ[日本]は？'),
        ('実は、材料で最強。', '実は[材料]で最強'),
        ('フォトレジストは、世界シェア9割。', 'フォトレジスト/世界シェア[9割]'),
        ('熊本にはティーエスエムシー、', '熊本に[TSMC]'),
        ('北海道では、ラピダスが2ナノに挑戦中よ。', '北海道で[Rapidus]が/2nmに挑戦'),
    ]),
    ('cta', 0.3, 1.5, [
        ('砂から始まって、世界を動かす。', '砂から始まり[世界]を動かす'),
        ('次に勝つのは、どの国だと思う?', '次に勝つのは[どの国]？'),
        ('コメントで教えて。', '[コメント]で教えて！'),
    ]),
]
PUNCT = set('、。?？!！,')

def _first(pattern):
    m = sorted(glob.glob(pattern)); return m[0] if m else ''

class Voicevox:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT') or
                                    _first(os.path.join(VENDOR, 'ort', '*', 'lib', 'libvoicevox_onnxruntime.so')))
        dic = os.environ.get('VOICEVOX_DICT') or _first(os.path.join(VENDOR, 'dict', 'open_jtalk_dic_utf_8-*'))
        self.synth = Synthesizer(ort, OpenJtalk(dic))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', os.path.join(VENDOR, 'vvms')), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        self.name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', self.name)

    def __call__(self, text):
        """音声と、句読点ごとの『次のフレーズが始まる時刻』のリストを返す"""
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = SPEED
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.08
        q.intonation_scale = 1.15   # 抑揚をやや強めにして耳を引く
        t = q.pre_phoneme_length / SPEED; bounds = []
        for ap in q.accent_phrases:
            t += sum((m.consonant_length or 0) + m.vowel_length for m in ap.moras) / SPEED
            if ap.is_interrogative: t += 0.15 / SPEED   # 疑問文の語尾上げで追加される母音
            if ap.pause_mora:
                p = ap.pause_mora
                t += (p['vowel_length'] if isinstance(p, dict) else p.vowel_length) / SPEED
                bounds.append(t)
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
        f = 300; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x, bounds

def main():
    engine = Voicevox()
    t = 0.0; scenes = []; subs = []; pieces = []
    for sid, lead, tail, phrases in SCRIPT:
        text = ''.join(r for r, _ in phrases)
        x, bounds = engine(text)
        speech = len(x) / SR
        # 各フレーズ末尾までの句読点数 → 次フレーズの開始時刻
        starts = [0.0]; count = 0
        for r, _ in phrases[:-1]:
            count += sum(ch in PUNCT for ch in r)
            starts.append(bounds[count - 1])
        ends = starts[1:] + [speech]
        s0 = t + lead
        for (r, d), a, b in zip(phrases, starts, ends):
            subs.append({'s': round(s0 + a, 3), 'e': round(s0 + b, 3), 'text': d, 'scene': sid})
        dur = lead + speech + tail
        scenes.append({'id': sid, 's': round(t, 3), 'd': round(dur, 3), 'v0': round(lead, 3), 'v1': round(lead + speech, 3),
                       'phr': [round(lead + a, 3) for a in starts]})
        pieces.append((s0, x))
        print(f'{t:5.2f}s  {sid:7s} speech {speech:5.2f}s  scene {dur:5.2f}s  phrases at ' + ' '.join(f'{lead + a:.2f}' for a in starts))
        t += dur
    total = round(t, 3)
    track = np.zeros(int(total * SR) + 1, dtype=np.float32)
    for s0, x in pieces:
        i = int(s0 * SR); track[i:i + len(x)] += x[:len(track) - i]
    track = track / (np.max(np.abs(track)) or 1) * 0.89
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    tl = {'total': total, 'voice': engine.name, 'scenes': scenes, 'subtitles': subs}
    with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('window.TIMELINE = ' + json.dumps(tl, ensure_ascii=False) + ';\n')
    def ts(v):
        h = int(v // 3600); m = int(v % 3600 // 60); sec = v % 60
        return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, c in enumerate(subs, 1):
            f.write(f"{i}\n{ts(c['s'])} --> {ts(c['e'])}\n{c['text'].replace('[', '').replace(']', '').replace('/', ' ')}\n\n")
    print(f'total {total:.2f}s -> output/narration.wav, timeline.json, timeline.js, subtitles_ja.srt')

if __name__ == '__main__':
    main()
