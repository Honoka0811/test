# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX: 四国めたん)を文ごとに合成し、シーンのタイムライン・字幕(フレーズ単位)を書き出す。
出力: output/narration.wav, output/timeline.json, output/subtitles_ja.srt
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(0.vvm に四国めたんが入っている)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.25'))

# シーン定義。各文は [(字幕テキスト, 読み上げテキスト), ...] のフレーズ列。読み上げ側は「、」で連結する。
# 固有名詞は読み間違いを防ぐためにかなで渡す。
SCENES = [
    dict(id='hook', lead=0.35, tail=0.15, sentences=[
        [('海外、行かなくてよくない？', 'かいがい、行かなくてよくない？')],
        [('日本の"世界レベル"絶景', 'ニホンノ、世界レベル絶景'), ('5つ、いくよ', '五つ、いくよ')],
    ]),
    dict(id='r5', rank=5, place='角島大橋', pref='山口県', lead=0.45, tail=0.55, sentences=[
        [('第5位', '第五位'), ('山口県', '山口県'), ('角島大橋', '角島大橋')],
        [('エメラルドの海の上を', 'エメラルドの海の上を'), ('1,780m', '千七百八十メートル'), ('一直線', 'いっちょくせん')],
        [('しかも通行無料', 'しかも、つうこうむりょう')],
    ]),
    dict(id='r4', rank=4, place='与那覇前浜', pref='宮古島', lead=0.45, tail=0.55, sentences=[
        [('第4位', '第四位'), ('宮古島', 'みやこじま'), ('与那覇前浜', 'ヨナハ、マエハマ')],
        [('7kmの白い砂浜と', 'ななキロの、白い砂浜と'), ('透き通る海', '透き通る海')],
        [('"東洋一"のビーチ', '東洋一のビーチ')],
    ]),
    dict(id='r3', rank=3, place='竹田城跡', pref='兵庫県', lead=0.45, tail=0.55, sentences=[
        [('第3位', '第三位'), ('兵庫県', '兵庫県'), ('竹田城跡', 'たけだじょうせき')],
        [('秋の早朝', '秋の早朝'), ('雲海に浮かぶ"天空の城"', 'うんかいに浮かぶ、天空の城')],
        [('狙い目は', 'ねらいめは'), ('晴れた日の夜明け前', '晴れた日の、夜明け前')],
    ]),
    dict(id='r2', rank=2, place='青ヶ島', pref='東京都', lead=0.45, tail=0.55, sentences=[
        [('第2位', '第二位'), ('東京都', '東京都'), ('青ヶ島', 'アオガシマ')],
        [('世界でも珍しい', '世界でもめずらしい'), ('二重カルデラの島', 'にじゅうカルデラの島')],
        [('人口 約170人', '人口、約百七十人'), ('行けるのは船かヘリだけ', '行けるのは、船かヘリだけ')],
    ]),
    dict(id='r1', rank=1, place='父母ヶ浜', pref='香川県', lead=0.8, tail=0.7, sentences=[
        [('そして第1位', 'そして、第一位'), ('香川県', '香川県'), ('父母ヶ浜', 'チチブガハマ')],
        [('干潮と夕暮れが重なる瞬間', 'かんちょうと夕暮れが重なる瞬間'), ('浜が、鏡になる', '浜が、鏡になる')],
        [('"日本のウユニ塩湖"', 'ニホンノ、ウユニエンコ')],
    ]),
    dict(id='cta', lead=0.45, tail=1.5, sentences=[
        [('次の休み、どこ行く？', '次の休み、どこ行く？')],
        [('行きたい場所', '行きたい場所'), ('コメントで教えてね', 'コメントでおしえてね')],
        [('保存して旅の計画に', '保存して、旅の計画に')],
    ]),
]
GAP = 0.12  # 文と文の間

# 読み・アクセントの補正(AquesTalk 風記法)。VOICEVOX が文から作った kana を置換し、create_audio_query_from_kana で作り直す。
# ' はアクセント核(直前のモーラの後で下がる)、/ はアクセント句の区切り、、は息継ぎ、_ は無声化。
KANA_FIXES = [
    ("マ'エ/ハマ'", "マエハマ'"),              # 与那覇前浜: マエ/ハマ と切れる → 1語に
    ("タケ'ダ/ジョオセキ'", "タケダジョ'オセキ"),  # 竹田城跡
    ("ヨアケ'/マ'エ", "ヨアケマ'エ"),            # 夜明け前
    ("アオガシマ'", "アオガ'シマ"),              # 青ヶ島
    ("チ'チ/ブガ'ハマ", "チチブガ'ハマ"),         # 父母ヶ浜: チチ/ブガハマ と切れる → 1語に
]
_fix_used = set()

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class Metan:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)

    def sentence(self, phrases, speed=SPEED):
        """1文を合成。戻り値: (wav float32 @SR, [(start, end, caption), ...])"""
        text = '、'.join(p[1] for p in phrases)
        q = self.synth.create_audio_query(text, self.style)
        kana = q.kana
        for k, (old, new) in enumerate(KANA_FIXES):
            if old in kana:
                kana = kana.replace(old, new); _fix_used.add(k)
        if kana != q.kana:
            q = self.synth.create_audio_query_from_kana(kana, self.style)
        print('  ', kana)
        q.speed_scale = speed
        q.intonation_scale = 1.15     # 抑揚を少し強めにして元気に
        q.pitch_scale = 0.01
        q.pre_phoneme_length = 0.06
        q.post_phoneme_length = 0.08
        # 読点「、」で区切られたアクセント句グループ → フレーズの時間
        groups = []; cur = 0.0; t = q.pre_phoneme_length
        for ap in q.accent_phrases:
            d = sum(((m['consonant_length'] if isinstance(m, dict) else m.consonant_length) or 0.0) + (m['vowel_length'] if isinstance(m, dict) else m.vowel_length) for m in ap.moras)
            cur += d
            if ap.pause_mora is not None:
                groups.append((t, t + cur)); pm = ap.pause_mora; t += cur + (pm["vowel_length"] if isinstance(pm, dict) else pm.vowel_length); cur = 0.0
        if cur > 0: groups.append((t, t + cur))
        groups = [(a / speed, b / speed) for a, b in groups]
        # 読み上げ側の「、」数と字幕フレーズ数が一致しない場合は、読み上げ側の読点でできたグループを字幕フレーズ数に束ねる
        caps = [p[0] for p in phrases]
        if len(groups) != len(caps):
            counts = [p[1].count('、') + 1 for p in phrases]
            if sum(counts) == len(groups):
                merged = []; i = 0
                for c in counts:
                    merged.append((groups[i][0], groups[i + c - 1][1])); i += c
                groups = merged
            else:
                print('  [warn] phrase/group mismatch', len(groups), len(caps), text)
                n = sum(len(c) for c in caps); tot = groups[-1][1] - groups[0][0]; a = groups[0][0]; groups = []
                for c in caps:
                    groups.append((a, a + tot * len(c) / n)); a += tot * len(c) / n
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        return x, list(zip([g[0] for g in groups], [g[1] for g in groups], caps))

engine = Metan()

# ---------- 文ごとに合成してシーンを並べる ----------
timeline = []; chunks = []; t = 0.0
for sc in SCENES:
    start = t
    t += sc['lead']
    sents = []
    for si, phrases in enumerate(sc['sentences']):
        x, cues = engine.sentence(phrases)
        n = len(x); f = min(480, n // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        chunks.append((t, x))
        sents.append(dict(start=t, end=t + n / SR, phrases=[dict(start=t + a, end=t + b, text=c) for a, b, c in cues]))
        t += n / SR + GAP
    t += sc['tail'] - GAP
    timeline.append(dict(id=sc['id'], rank=sc.get('rank'), place=sc.get('place'), pref=sc.get('pref'),
                         start=round(start, 3), end=round(t, 3), sentences=sents))
    print(f"{sc['id']:5s} {start:6.2f} → {t:6.2f}  ({t - start:4.1f}s)")

for k, (old, new) in enumerate(KANA_FIXES):
    if k not in _fix_used: print('[warn] 未使用の読み補正:', old)
TOTAL = round(t, 3)
track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s, x in chunks:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(total=TOTAL, scenes=timeline), f, ensure_ascii=False, indent=1)

def _ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 1
    for sc in timeline:
        for se in sc['sentences']:
            f.write(f"{i}\n{_ts(se['start'])} --> {_ts(se['end'] + 0.2)}\n{'、'.join(p['text'] for p in se['phrases'])}\n\n"); i += 1
print('total', TOTAL, 's  wrote narration.wav / timeline.json / subtitles_ja.srt')
