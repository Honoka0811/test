# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、不気味系BGM(bgm.py)をダッキングしながらミックスする。
出力:
  output/narration.wav   ナレーションのみ
  output/mix.wav         ナレーション + BGM + 効果音
  output/subtitles_ja.srt 字幕
  output/cues.js         render.html が読む焼き込み字幕のタイミング
使い方: python3 narrate.py
環境変数:
  VOICEVOX_URL   VOICEVOX ENGINE の URL(既定 http://127.0.0.1:50021)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。36 = ささやき, 37 = ヒソヒソ)
"""
import os, io, re, json, wave, urllib.request, urllib.parse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
URL = os.environ.get('VOICEVOX_URL', 'http://127.0.0.1:50021')
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))

SR = 48000
TOTAL = 72.0
LEAD = 0.5   # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 読み上げ原稿, 字幕表記)  render.html の SCENES と対応
SCRIPT = [
    (0, 7,
     '千九百四十九年、七月。国鉄の総裁が、こつぜんと姿を消しました。',
     '1949年7月。国鉄の総裁が、忽然と姿を消しました。'),
    (7, 9.5,
     '七月五日の朝。下山定則総裁は、日本橋の三越に入ったまま、二度と戻りませんでした。',
     '7月5日の朝。下山定則総裁は、日本橋の三越に入ったまま、二度と戻りませんでした。'),
    (16.5, 8.5,
     'その前日、国鉄は、約三万人の人員整理を通告していました。',
     'その前日、国鉄は、約3万人の人員整理を通告していました。'),
    (25, 9,
     '翌日の深夜。じょうばん線の線路の上で、列車にひかれた総裁の遺体が見つかります。',
     '翌日の深夜。常磐線の線路の上で、列車に轢かれた総裁の遺体が見つかります。'),
    (34, 13,
     'しかし、奇妙な点がありました。遺体の周りには、血がほとんど残っていない。衣服には、大量の油と色素。そして近くの旅館では、総裁によく似た男が目撃されていました。',
     'しかし、奇妙な点がありました。遺体の周りには、血がほとんど残っていない。衣服には、大量の油と色素。そして近くの旅館では、総裁によく似た男が目撃されていました。'),
    (47, 10,
     '東大は、死後にひかれたとする他殺説。慶應は、生きたままひかれたとする自殺説。鑑定は、真っ向から対立します。',
     '東大は、死後に轢かれたとする他殺説。慶應は、生きたまま轢かれたとする自殺説。鑑定は、真っ向から対立します。'),
    (57, 9,
     '同じ夏、三鷹事件、松川事件が相次ぎ、千九百六十四年、事件は時効を迎えました。',
     '同じ夏、三鷹事件、松川事件が相次ぎ、1964年、事件は時効を迎えました。'),
    (66, 6,
     '真相は、今も、闇の中です。',
     '真相は、今も、闇の中です。'),
]

def api(path, params, body=None):
    req = urllib.request.Request(f'{URL}{path}?{urllib.parse.urlencode(params)}',
                                 data=body if body is not None else b'', method='POST',
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def tts(text, speed):
    q = json.loads(api('/audio_query', {'text': text, 'speaker': STYLE}))
    q.update(speedScale=speed, pitchScale=-0.02, intonationScale=0.95, volumeScale=1.0,
             prePhonemeLength=0.05, postPhonemeLength=0.1, outputSamplingRate=SR, outputStereo=False)
    wav = api('/synthesis', {'speaker': STYLE}, json.dumps(q).encode())
    with wave.open(io.BytesIO(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        assert w.getframerate() == SR
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

def main():
    names = {st['id']: f"{sp['name']}/{st['name']}" for sp in json.load(urllib.request.urlopen(f'{URL}/speakers'))
             for st in sp['styles']}
    print('engine: VOICEVOX', names.get(STYLE))
    track = np.zeros(int(TOTAL * SR), dtype=np.float32)
    cues = []      # 字幕(文単位)
    voiced = []    # (開始, 終了) 発話区間
    for start, dur, text, sub in SCRIPT:
        limit = dur - LEAD - 0.5
        speed = 1.08  # 基準速度。収まらなければ少しずつ上げる
        for _ in range(6):
            x = tts(text, speed)
            sec = len(x) / SR
            if sec <= limit:
                break
            speed = min(speed * (sec / limit) * 1.02, 1.3)
        print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {sub[:20]}…')
        n = len(x); f = min(600, n // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        s = int((start + LEAD) * SR); e = min(s + n, len(track))
        track[s:e] += x[:e - s]
        a, b = start + LEAD, start + LEAD + n / SR
        voiced.append((a, b))
        # 字幕を「。」で文に分け、読みの文字数比で時間を割り振る
        subs = [p for p in re.split(r'(?<=。)', sub) if p]
        reads = [p for p in re.split(r'(?<=。)', text) if p]
        if len(subs) != len(reads):
            subs, reads = [sub], [text]
        w_ = np.array([len(r) for r in reads], dtype=float); w_ /= w_.sum()
        t = a
        for p, ww in zip(subs, w_):
            cues.append({'s': round(t, 3), 'e': round(t + (b - a) * ww, 3), 'text': p})
            t += (b - a) * ww

    peak = np.max(np.abs(track)) or 1
    track = track / peak * 0.85
    write_wav(os.path.join(OUT, 'narration.wav'), track)

    with open(os.path.join(OUT, 'cues.js'), 'w', encoding='utf-8') as f:
        f.write('window.CUES = ' + json.dumps(cues, ensure_ascii=False, indent=1) + ';\n')
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{_ts(c['s'])} --> {_ts(min(c['e'] + 0.2, TOTAL))}\n{c['text']}\n\n")

    # ---------- BGM + 効果音 をダッキングしながらミックス ----------
    import bgm as bgm_mod
    music = bgm_mod.generate(TOTAL)
    sfx = bgm_mod.sfx(TOTAL)
    music = fit(music, len(track)); sfx = fit(sfx, len(track))
    hop = SR // 20
    rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
    envl = np.zeros_like(rms)
    for i, v in enumerate(rms):
        envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
    envl = np.pad(np.repeat(envl, hop), (0, len(track) - len(rms) * hop))
    speech = np.clip(envl / 0.12, 0, 1)
    BGM_SILENT, BGM_SPEECH = 0.50, 0.15
    gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
    k = SR // 10
    gain = np.convolve(gain, np.ones(k) / k, mode='same')
    sfx_gain = np.convolve(0.6 - 0.3 * speech, np.ones(k) / k, mode='same')
    mixed = track + music * gain + sfx * sfx_gain
    mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
    write_wav(os.path.join(OUT, 'mix.wav'), mixed)
    write_wav(os.path.join(OUT, 'bgm.wav'), music)
    print('wrote output/narration.wav, mix.wav, bgm.wav, subtitles_ja.srt, cues.js')

def fit(x, n):
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))

def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000: ms = 999
    return f'{h:02d}:{m:02d}:{int(sec):02d},{ms:03d}'

if __name__ == '__main__':
    main()
