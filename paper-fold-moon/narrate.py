# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん ノーマル)を合成し、各行の尺から動画のタイムラインを作る。
VOICEVOX ENGINE を http://127.0.0.1:50021 で起動しておくこと。
出力: output/narration.wav, output/timeline.json, output/subtitles_ja.srt
"""
import os, io, json, wave, urllib.request, urllib.parse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
HOST = os.environ.get('VOICEVOX_HOST', 'http://127.0.0.1:50021')
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))  # 2 = 四国めたん ノーマル
SR = 48000
SPEED = 1.26
HEAD = 0.25   # 動画冒頭からナレーション開始まで
TAIL = 2.6    # 最後の行の後の余韻

# (シーンID, 読み上げ用テキスト, 字幕テキスト, 次の行までの間[秒])
LINES = [
    ('hook',   '厚さ、れい点いちミリの紙を、よんじゅうに回折ると、月に届きます。', '厚さ0.1ミリの紙を\n42回折ると、月に届きます', 0.35),
    ('doubt',  'ウソだと思いました？でも、計算すると、本当なんです。', 'ウソだと思いました？\nでも計算すると、本当なんです', 0.25),
    ('f10',    '一回折るごとに、厚さは二倍。十回で、約十センチ。スマホくらいです。', '1回折るごとに厚さは2倍\n10回で約10cm スマホくらい', 0.15),
    ('f20',    '二十回で、約百メートル。三十階建てのビルを超えます。', '20回で約100m\n30階建てのビルを超える', 0.15),
    ('f30',    '三十回で、約百キロ。もう、宇宙です。', '30回で約100km\nもう宇宙です', 0.15),
    ('f42',    'そして、よんじゅうに回目。約四十四万キロ。月までの三十八万キロを、超えました。', 'そして42回目\n約44万km 月までの38万kmを超えた', 0.55),
    ('half',   'でも、本当にすごいのはここからです。よんじゅういち回目の時点では、まだ、月までの半分ちょっと。', '本当にすごいのはここから\n41回目では、まだ月までの半分ちょっと', 0.2),
    ('last',   'つまり、全体の半分は、最後のたった一回で、生まれるんです。', '全体の半分は\n最後のたった1回で生まれる', 0.5),
    ('life',   'これは、毎日も同じ。毎日一パーセント成長すると、一年で、約三十八倍。', 'これは毎日も同じ\n毎日1%成長すると 1年で約38倍', 0.15),
    ('lazy',   '毎日一パーセントサボると、一年で、れい点れいさん倍。', '毎日1%サボると\n1年で0.03倍', 0.6),
    ('quit',   '成果が見えなくて、やめたくなった時。それは、よんじゅういち回目かもしれません。', '成果が見えなくて やめたくなった時\nそれは「41回目」かもしれない', 0.5),
    ('ask',    'あなたは今、何回目ですか？', 'あなたは今、何回目ですか？', 0.0),
]


def post(path, params, body=None):
    url = HOST + path + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=body or b'', method='POST',
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as r:
        return r.read()


def synth(text):
    q = json.loads(post('/audio_query', {'text': text, 'speaker': STYLE}))
    q['speedScale'] = SPEED
    q['intonationScale'] = 1.15
    q['prePhonemeLength'] = 0.05
    q['postPhonemeLength'] = 0.08
    q['outputSamplingRate'] = SR
    wav = post('/synthesis', {'speaker': STYLE}, json.dumps(q).encode())
    # アクセント句ごとの開始時刻(未スケール)を計算し、実際の長さに合わせて後で補正する
    marks, t = [], q['prePhonemeLength']
    for ap in q['accent_phrases']:
        marks.append([''.join(m['text'] for m in ap['moras']), t])
        for m in ap['moras']:
            t += (m.get('consonant_length') or 0) + m['vowel_length']
        if ap.get('pause_mora'):
            t += ap['pause_mora']['vowel_length']
    t += q['postPhonemeLength']
    with wave.open(io.BytesIO(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(1)
    k = len(x) / SR / t
    return x, [[txt, round(tt * k, 3)] for txt, tt in marks]


def srt_time(t):
    ms = int(round(t * 1000))
    return '%02d:%02d:%02d,%03d' % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def main():
    os.makedirs(OUT, exist_ok=True)
    clips, timeline, t = [], [], HEAD
    for sid, read, sub, gap in LINES:
        x, marks = synth(read)
        d = len(x) / SR
        timeline.append({'id': sid, 'start': round(t, 3), 'dur': round(d, 3), 'text': sub, 'marks': marks})
        clips.append((t, x))
        print('%-6s %6.2f  +%.2fs  %s' % (sid, t, d, sub.replace('\n', ' ')))
        t += d + gap
    total = t + TAIL
    buf = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for st, x in clips:
        s = int(st * SR)
        buf[s:s + len(x)] += x
    buf = buf[:int(total * SR)]
    buf = buf / max(1e-6, np.abs(buf).max()) * 0.89
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump({'total': round(total, 3), 'lines': timeline}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, l in enumerate(timeline, 1):
            f.write('%d\n%s --> %s\n%s\n\n' % (i, srt_time(l['start']), srt_time(l['start'] + l['dur'] + 0.15),
                                               l['text'].replace('\n', ' ')))
    print('total %.2fs' % total)


if __name__ == '__main__':
    main()
