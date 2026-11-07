# -*- coding: utf-8 -*-
"""VOICEVOX(四国めたん)でシーンごとのナレーションを合成し、
テロップ(チャンク)ごとの開始/終了時刻をモーラ長から算出して output/timing.js に書き出す。

使い方: python3 narrate.py
環境変数:
  VOICEVOX_URL    VOICEVOX ENGINE の URL(省略時は 127.0.0.1:50021 → 公開ミラーの順に自動検出)
  VOICEVOX_STYLE  スタイルID(既定 2 = 四国めたん ノーマル。0=あまあま 6=ツンツン 4=セクシー)
生成物: output/narration.wav(48kHz mono) / output/timing.js / output/subtitles_ja.srt
"""
import os, sys, io, json, wave, time, hashlib, urllib.request, urllib.parse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(OUT, 'cache'); os.makedirs(CACHE, exist_ok=True)
SR = 48000
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))

# 話し方のパラメータ(元気でテンポよく)
SPEED, INTONATION, PITCH, PAUSE = 1.12, 1.3, 0.0, 0.8
PRE, POST = 0.04, 0.08          # 文頭/文末の無音(秒、話速で割られる)
GAP = 0.32                      # シーン間の間(秒)
HEAD = 0.55                     # 最初のナレーションまでの間(フック演出用)

# ---------------------------------------------------------------------------
# 原稿。シーンごとに「テロップのチャンク」の並び。各チャンクは必ず句読点で終える
# (アクセント句の境界を揃えるため)。【】で囲んだ語はテロップで強調表示される。
# 'speak' を付けると読み上げ用の文字列を別に指定できる。
SCENES = [
    dict(id='hook', chunks=[
        '習慣が続かないのは、',
        '【意志が弱い】からじゃない。',
    ]),
    dict(id='promise', chunks=[
        '続く人がこっそりやってる、',
        '【5つのコツ】、',
        '全部見せます。',
    ]),
    dict(id='tip1', n=1, title='2分で終わる形にする', chunks=[
        'その1、【2分で終わる形】にする。',
        '腕立て30回じゃなくて、【1回】。',
        '読書30分じゃなくて、【1ページ】。',
        '始めるハードルを、【地面まで】下げる。',
    ]),
    dict(id='tip2', n=2, title='今ある習慣にくっつける', chunks=[
        'その2、【今ある習慣】にくっつける。',
        '歯みがきのあとに、【スクワット10回】。',
        'コーヒーを入れたら、【英単語3つ】。',
        'セットにすれば、【忘れない】。',
    ]),
    dict(id='tip3', n=3, title='意志より環境を変える', chunks=[
        'その3、意志より【環境】を変える。',
        'スマホは【別の部屋】、',
        '本は【枕の上】。',
        'やる気に頼った時点で、【負け】。',
    ]),
    dict(id='tip4', n=4, title='やったらカレンダーにマル', chunks=[
        'その4、やったら【カレンダーにマル】。',
        'マルの列が伸びるほど、',
        '【途切れさせたくなく】なる。',
    ]),
    dict(id='tip5', n=5, title='サボるなら1日だけ', chunks=[
        dict(text='その5、サボるなら【1日だけ】。', speak='その5、サボるなら、いちにちだけ。'),
        '1回休むのは【事故】。',
        '2回続いたら、それが【新しい習慣】。',
    ]),
    dict(id='cta', chunks=[
        '全部やらなくていい。',
        '明日の朝、【1つだけ】試して。',
        '結果は、【コメント】で教えてね。',
    ]),
]

def norm(c):
    if isinstance(c, str): c = dict(text=c)
    c.setdefault('speak', c['text'].replace('【', '').replace('】', ''))
    c['display'] = c['text']
    return c

# ---------------------------------------------------------------------------
CANDIDATES = [os.environ.get('VOICEVOX_URL'), 'http://127.0.0.1:50021',
              'https://jahirrrr-voicevox-engine.hf.space', 'https://meowsky49887-voicevox-engine.hf.space']

def http(url, data=None, headers=None, timeout=90):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def pick_engine():
    for base in [c for c in CANDIDATES if c]:
        try:
            v = http(base + '/version', timeout=15).decode()
            sp = json.loads(http(base + '/speakers', timeout=20))
            name = next((s['name'] + '/' + st['name']) for s in sp for st in s['styles'] if st['id'] == STYLE)
            print(f'engine: {base}  version={v.strip()}  style={STYLE} ({name})')
            return base
        except Exception as e:
            print(f'  skip {base}: {e}')
    sys.exit('VOICEVOX ENGINE が見つかりません。VOICEVOX_URL を指定してください。')

BASE = pick_engine()

def retry(fn, n=5):
    for i in range(n):
        try: return fn()
        except Exception as e:
            print(f'   retry {i+1}/{n}: {e}'); time.sleep(2 * (i + 1))
    raise RuntimeError('engine request failed')

def audio_query(text):
    key = hashlib.md5(f'q|{STYLE}|{text}'.encode()).hexdigest()
    p = os.path.join(CACHE, key + '.json')
    if os.path.exists(p): return json.load(open(p, encoding='utf-8'))
    q = urllib.parse.urlencode({'text': text, 'speaker': STYLE})
    d = json.loads(retry(lambda: http(f'{BASE}/audio_query?{q}', data=b'')))
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    return d

def synthesis(query):
    body = json.dumps(query, ensure_ascii=False).encode()
    key = hashlib.md5(b's|' + str(STYLE).encode() + body).hexdigest()
    p = os.path.join(CACHE, key + '.wav')
    if not os.path.exists(p):
        wav = retry(lambda: http(f'{BASE}/synthesis?speaker={STYLE}', data=body,
                                 headers={'Content-Type': 'application/json'}, timeout=180))
        open(p, 'wb').write(wav)
    with wave.open(p) as w:
        sr = w.getframerate(); ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if ch == 2: x = x.reshape(-1, 2).mean(1)
    if sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    return x

def mora_units(q):
    """accent_phrases を (長さ秒, ポーズか) のモーラ列に展開(話速適用前)"""
    units = []
    for ap in q['accent_phrases']:
        for m in ap['moras']:
            units.append(((m.get('consonant_length') or 0.0) + m['vowel_length'], False))
        if ap.get('pause_mora'):
            units.append((ap['pause_mora']['vowel_length'] * PAUSE, True))
    return units

def count_moras(q):
    """ポーズを除いたモーラ数"""
    return sum(len(ap['moras']) for ap in q['accent_phrases'])

track = []
timeline = []           # シーン情報
t = HEAD
srt = []
for sc in SCENES:
    chunks = [norm(c) for c in sc['chunks']]
    full = ''.join(c['speak'] for c in chunks)
    q = audio_query(full)
    q.update(speedScale=SPEED, intonationScale=INTONATION, pitchScale=PITCH, pauseLengthScale=PAUSE,
             prePhonemeLength=PRE, postPhonemeLength=POST, outputSamplingRate=SR, outputStereo=False)
    x = synthesis(q)
    # ---- チャンクごとのタイミング(モーラ数でフル音声を分割) ----
    units = mora_units(q)
    counts = [count_moras(audio_query(c['speak'])) for c in chunks]
    if sum(counts) != sum(1 for _, p in units if not p):
        sys.exit(f'モーラ数が一致しません: {sc["id"]} full={sum(1 for _, p in units if not p)} chunks={counts}\n  {q["kana"]}')
    pred = (PRE + POST + sum(d for d, _ in units)) / SPEED
    actual = len(x) / SR
    scale = actual / pred            # 実測の長さに合わせて補正(数%以内のはず)
    print(f'{sc["id"]:8s} {actual:5.2f}s (pred {pred:5.2f}s, x{scale:.3f})  {q["kana"][:44]}')
    pos = PRE / SPEED * scale
    cues = []
    i = 0
    for c, n in zip(chunks, counts):
        spoken = 0.0; k = 0
        while k < n:                              # 非ポーズのモーラを n 個消費
            d, p = units[i]; i += 1
            spoken += d
            if not p: k += 1
        tail = 0.0
        if i < len(units) and units[i][1]:         # 直後の句読点ポーズはこのチャンクに帰属(表示は終える)
            tail = units[i][0]; i += 1
        cues.append(dict(text=c['display'], start=round(t + pos, 3), end=round(t + pos + spoken / SPEED * scale, 3)))
        pos += (spoken + tail) / SPEED * scale
    start = t
    t_end = t + actual
    timeline.append(dict(id=sc['id'], n=sc.get('n'), title=sc.get('title'), start=round(start, 3),
                         speech_end=round(t_end, 3), chunks=cues))
    track.append((start, x))
    for c in cues:
        srt.append((c['start'], c['end'] + 0.25, c['text'].replace('【', '').replace('】', '')))
    t = t_end + GAP

# 各シーンの end = 次のシーンの start(最後は余韻を付ける)
for a, b in zip(timeline, timeline[1:]): a['end'] = b['start']
timeline[-1]['end'] = round(timeline[-1]['speech_end'] + 1.6, 3)
TOTAL = timeline[-1]['end']

buf = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for start, x in track:
    f = min(240, len(x) // 4); x = x.copy(); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int(start * SR); buf[s:s + len(x)] += x
buf = buf[:int(TOTAL * SR)]
buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())

# 30fps の音量包絡(画面の波形演出用)
FPS = 30
hop = SR // FPS
env = np.sqrt(np.mean(buf[:len(buf) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = (env / (env.max() + 1e-9)).round(3).tolist()

with open(os.path.join(OUT, 'timing.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMING = ' + json.dumps(dict(total=round(TOTAL, 3), fps=FPS, scenes=timeline, env=env), ensure_ascii=False) + ';\n')

def ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, text) in enumerate(srt, 1):
        f.write(f'{i}\n{ts(a)} --> {ts(min(b, TOTAL))}\n{text}\n\n')
print(f'total {TOTAL:.2f}s  -> output/narration.wav, output/timing.js, output/subtitles_ja.srt')
