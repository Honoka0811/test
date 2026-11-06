# -*- coding: utf-8 -*-
"""英語ナレーションを VOICEVOX(四国めたん)で合成し、タイムライン(timeline.js)と英語字幕(SRT)を書き出す。

VOICEVOX は日本語エンジンなので、英文をそのまま渡すとアルファベットを1文字ずつ読んでしまう。
そこで各フレーズを「カタカナ英語」で書き、画面字幕は正しい英語で表示する。
フレーズ単位でモーラ長を合計して、字幕を声にぴったり合わせる(カラオケ風キャプション)。

使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, glob, json, wave, copy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = 1.22
GAP = 0.5      # シーン間の間(秒)
LEAD = 0.15     # シーン開始からナレーション開始まで

# シーンごとに (英語字幕, カタカナ読み) のフレーズ列。*word* は字幕で強調(黄色)する語。
SCENES = [
    ('hook', [
        ('Octopuses are basically *ALIENS*.', 'オクトパスィズアーベイスィカリーエイリアンズ。'),
        ('Here are *5 facts* that sound *fake*,', 'ヒアアーファイブファクツザットサウンドフェイク、'),
        ('but are totally *real!*', 'バットアートータリーリアル!'),
    ]),
    ('hearts', [
        ('Number *five*.', 'ナンバーファイブ。'),
        ('They have *THREE hearts!*', 'ゼイハヴスリーハーツ!'),
        ('And the main one *stops beating*', 'アンドザメインワンストップスビーティング、'),
        ('when they *swim*.', 'ウェンゼイスウィム。'),
    ]),
    ('blood', [
        ('Number *four*.', 'ナンバーフォー。'),
        ('Their blood is *BLUE!*', 'ゼアブラッドイズブルー!'),
        ('It uses *copper*', 'イットユーズィズカッパー、'),
        ('instead of *iron*.', 'インステッドオブアイアン。'),
    ]),
    ('brains', [
        ('Number *three*.', 'ナンバースリー。'),
        ('They have *NINE brains!*', 'ゼイハヴナインブレインズ!'),
        ('One big brain,', 'ワンビッグブレイン、'),
        ('plus a *mini brain* in every arm.', 'プラスアミニブレインインエヴリーアーム。'),
    ]),
    ('taste', [
        ('Number *two*.', 'ナンバートゥー。'),
        ('They *TASTE* with their arms!', 'ゼイテイストウィズゼアアームズ!'),
        ('Every sucker works', 'エヴリーサカーワークス、'),
        ('like a *tiny tongue*.', 'ライカタイニータング。'),
    ]),
    ('color', [
        ('And number *ONE*...', 'アンドナンバーワン……'),
        ('They change color *in a blink*.', 'ゼイチェインジカラーインアブリンク。'),
        ('But scientists think', 'バットサイエンティスツシンク、'),
        ("they're *COLORBLIND!*", 'ゼイアーカラーブラインド!'),
    ]),
    ('outro', [
        ('Which fact *shocked you* most?', 'ウィッチファクトショックトユーモースト?'),
        ('*Comment* below!', 'コメントビロウ!'),
        ('Because seriously...', 'ビコーズスィリアスリー……'),
    ]),
]


def dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d:
        return d
    for c in ['/home/user/vv/open_jtalk_dic_utf_8-1.11']:
        if os.path.isdir(c):
            return c
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')


from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get(
    'VOICEVOX_ORT', '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('voice:', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))


def phrase_len(aps):
    """アクセント句列の長さ(秒, speed_scale=1)"""
    t = 0.0
    for ap in aps:
        for m in list(ap.moras) + ([ap.pause_mora] if ap.pause_mora else []):
            g = (lambda k: m.get(k)) if isinstance(m, dict) else (lambda k: getattr(m, k))
            t += (g('consonant_length') or 0) + g('vowel_length')
    return t


def synth_line(phrases):
    """1シーン分のフレーズを1つの AudioQuery にまとめて自然に合成し、各フレーズの開始/終了時刻を返す。"""
    queries = [synth.create_audio_query(k, STYLE) for _, k in phrases]
    q = copy.deepcopy(queries[0])
    q.accent_phrases = [ap for qq in queries for ap in qq.accent_phrases]
    q.speed_scale = SPEED
    q.intonation_scale = 1.35     # 抑揚を強めて元気に
    q.pitch_scale = 0.02
    q.volume_scale = 1.0
    q.pre_phoneme_length = 0.0
    q.post_phoneme_length = 0.15
    wav = synth.synthesis(q, STYLE)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    cues, t = [], 0.0
    for (en, _), qq in zip(phrases, queries):
        d = phrase_len(qq.accent_phrases) / SPEED
        cues.append([t, t + d, en])
        t += d
    return x, cues


track = []
timeline = []
cur = 0.0
for name, phrases in SCENES:
    x, cues = synth_line(phrases)
    start = cur
    vstart = start + LEAD
    dur = LEAD + len(x) / SR + GAP
    timeline.append({'name': name, 'start': round(start, 3), 'dur': round(dur, 3),
                     'cues': [[round(vstart + a, 3), round(vstart + b, 3), en] for a, b, en in cues]})
    track.append((vstart, x))
    print(f'{name:7s} {start:5.2f}s  len={dur:4.2f}s')
    cur += dur

TOTAL = round(cur + 0.4, 2)
timeline[-1]['dur'] = round(TOTAL - timeline[-1]['start'], 3)
buf = np.zeros(int(TOTAL * SR), dtype=np.float32)
for s, x in track:
    i = int(s * SR)
    buf[i:i + len(x)] += x[:len(buf) - i]
buf = buf / (np.max(np.abs(buf)) or 1) * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())

with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が自動生成。手で編集しない\n')
    f.write('window.TOTAL = %s;\nwindow.TIMELINE = %s;\n' % (TOTAL, json.dumps(timeline, ensure_ascii=False, indent=1)))
with open(os.path.join(OUT, 'timeline.json'), 'w') as f:
    json.dump({'total': TOTAL, 'scenes': timeline}, f, indent=1)


def ts(t):
    return '%02d:%02d:%02d,%03d' % (t // 3600, t % 3600 // 60, int(t % 60), round((t % 1) * 1000) % 1000)


with open(os.path.join(OUT, 'subtitles_en.srt'), 'w', encoding='utf-8') as f:
    i = 1
    for sc in timeline:
        for a, b, en in sc['cues']:
            f.write(f'{i}\n{ts(a)} --> {ts(b + 0.05)}\n{en.replace("*", "")}\n\n')
            i += 1
print('total', TOTAL, 's')
