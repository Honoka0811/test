# -*- coding: utf-8 -*-
"""シーンごとのナレーションを VOICEVOX(四国めたん ノーマル)で合成し、
音声の長さからシーン尺を決めて timing.js / 字幕SRT / narration.wav を書き出す。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, re, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.24     # 話速(全シーン共通)
LEAD = 0.35      # シーン開始から読み上げ開始まで
TAIL = 0.55      # 読み上げ終了からシーン切り替えまで

# (シーンID, 最低尺[秒], 読み上げ原稿, 字幕表記)
SCRIPT = [
    ('title', 4.5,
     '青春ジュウハチきっぷで巡る、おすすめルート五選。わたくし、四国めたんがご案内しますわ。',
     '青春18きっぷで巡る、おすすめルート5選。わたくし、四国めたんがご案内しますわ。'),
    ('tokaido', 0,
     'ひとつ目は、東海道本線。東京から大阪まで、普通列車だけでおよそ九時間。運賃にすると約九千円分なので、一日で十分に元が取れますのよ。',
     'ひとつ目は、東海道本線。東京から大阪まで、普通列車だけでおよそ9時間。運賃にすると約9千円分なので、1日で十分に元が取れますのよ。'),
    ('gono', 0,
     'ふたつ目は、ごのうせん。快速リゾートしらかみは、指定席券を買えば乗れますわ。窓いっぱいの日本海と、せんじょうじきの絶景は必見です。',
     'ふたつ目は、五能線。快速「リゾートしらかみ」は、指定席券を買えば乗れますわ。窓いっぱいの日本海と、千畳敷の絶景は必見です。'),
    ('tadami', 0,
     'みっつ目は、二千二十二年に全線で運転を再開した、只見線。川霧に包まれる、第一只見川橋梁は、まるで絵画のよう。本数が少ないので、時刻表の確認はお忘れなく。',
     'みっつ目は、2022年に全線で運転を再開した、只見線。川霧に包まれる第一只見川橋梁は、まるで絵画のよう。本数が少ないので、時刻表の確認はお忘れなく。'),
    ('yodo', 0,
     'よっつ目は、わたくしの地元、四国のよどせん。日本最後の清流、四万十川に寄り添って走り、トロッコ列車やホビートレインにも出会えますわ。',
     'よっつ目は、わたくしの地元、四国の予土線。日本最後の清流・四万十川に寄り添って走り、トロッコ列車やホビートレインにも出会えますわ。'),
    ('sanin', 0,
     'いつつ目は、日本一長い在来線、山陰本線。京都から下関方面まで、およそ六百七十キロ。餘部橋梁や、宍道湖の夕日を眺める、二日がかりの大旅行ですわ。',
     'いつつ目は、日本一長い在来線、山陰本線。京都から下関方面まで、およそ670キロ。餘部橋梁や宍道湖の夕日を眺める、2日がかりの大旅行ですわ。'),
    ('rules', 0,
     'きっぷは三日間用が一万円、五日間用が一万二千五十円。連続した日に使うきっぷで、特急や新幹線には乗れません。最新のルールは、JRの公式サイトで確認してくださいね。',
     'きっぷは3日間用が1万円、5日間用が1万2,050円。連続した日に使うきっぷで、特急や新幹線には乗れません。最新のルールは、JRの公式サイトで確認してくださいね。'),
    ('outro', 4.5,
     'あなたは、どのルートに乗ってみたいかしら。コメントで教えてくださいね。',
     'あなたは、どのルートに乗ってみたいかしら?コメントで教えてくださいね。'),
]


def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')


class Voicevox:
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

    def __call__(self, text):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = SPEED
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(self.synth.synthesis(q, self.style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        return x[max(0, idx[0] - 1200): idx[-1] + 2400] if len(idx) else x


def subtitle_chunks(sub, start, end):
    """字幕を句点・読点で 1〜2 行の塊に分け、文字数比で時間を割り振る"""
    MAX = 18
    chunks = []
    for sent in [x for x in re.split(r'(?<=[。?!])', sub) if x]:
        parts = [p for p in re.split(r'(?<=、)', sent) if p]
        cur = ''
        for p in parts:
            if cur and len(cur) + len(p) > MAX and len(cur) >= 6 and len(p) >= 6:
                chunks.append(cur); cur = p
            else:
                cur += p
        if cur:
            if chunks and len(cur) < 6 and len(chunks[-1]) + len(cur) <= 30 and not chunks[-1].endswith(('。', '?', '!')):
                chunks[-1] += cur
            else:
                chunks.append(cur)
    total = sum(len(c) for c in chunks)
    out, t = [], start
    for c in chunks:
        d = (end - start) * len(c) / total
        out.append((round(t, 3), round(t + d, 3), c.rstrip('、')))
        t += d
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    tts = Voicevox()
    clips, scenes, cues, t = [], [], [], 0.0
    for sid, min_dur, text, sub in SCRIPT:
        x = tts(text)
        sec = len(x) / SR
        dur = round(max(min_dur, LEAD + sec + TAIL), 2)
        scenes.append({'id': sid, 'start': round(t, 2), 'dur': dur})
        clips.append((t + LEAD, x))
        cues += subtitle_chunks(sub, t + LEAD, t + LEAD + sec)
        print(f'{sid:8s} start={t:5.2f}s voice={sec:4.2f}s scene={dur:4.2f}s')
        t += dur
    total = round(t + 0.5, 2)

    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for s, x in clips:
        x = x.copy(); f = min(600, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        i = int(s * SR); track[i:i + len(x)] += x
    track = track[:int(total * SR)]
    track = track / (np.max(np.abs(track)) or 1) * 0.85
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    timing = {'total': total, 'scenes': scenes, 'subs': cues}
    with open(os.path.join(HERE, 'timing.js'), 'w', encoding='utf-8') as f:
        f.write('// narrate.py が自動生成(シーン尺と字幕タイミング)\nwindow.TIMING = ')
        f.write(json.dumps(timing, ensure_ascii=False, indent=1))
        f.write(';\n')

    def ts(v):
        return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, (a, b, c) in enumerate(cues, 1):
            f.write(f'{i}\n{ts(a)} --> {ts(b)}\n{c}\n\n')
    print(f'total {total}s  -> timing.js, output/narration.wav, output/subtitles_ja.srt')


if __name__ == '__main__':
    main()
