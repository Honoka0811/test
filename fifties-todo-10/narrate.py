# -*- coding: utf-8 -*-
"""シーンごとのナレーションを VOICEVOX(四国めたん)で合成し、BGM(bgm.py)をダッキングしながらミックスする。
出力: output/narration.wav(声のみ) / output/bgm.wav(BGMのみ) / output/mix.wav(ミックス) / output/subtitles_ja.srt
動画との合成は export_upload.sh(または `python3 narrate.py --mux 入力mp4 出力mp4`)で行う。
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま, 6 = ツンツン, 4 = セクシー)
"""
import sys, os, io, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
WAV = os.path.join(OUT, 'narration.wav')
MIX = os.path.join(OUT, 'mix.wav')
SRT = os.path.join(OUT, 'subtitles_ja.srt')

SR = 48000
LEAD = 0.30                                 # シーン開始からナレーション開始までの間

# 読み上げ原稿(シーン順)。各シーンの長さはナレーションの実測長から決め、output/timeline.json に書き出す
SCRIPT = [
    '五十代のうちにやっておくべきこと、じゅっせん。テンポよく紹介します！',
    '一つ目、人間ドックで体の棚卸し。病気が見つかりやすい年代です。年に一度はしっかり調べましょう。',
    '二つ目、筋トレで筋肉貯金。筋肉は使わないと減る一方。スクワットとはやあるきから始めましょう。',
    '三つ目、歯のメンテナンス。歯を失うと食事も会話も変わります。三か月に一度はクリーニングを。',
    '四つ目、お金の見直し。年金、保険、資産をまとめて把握。六十歳からの収支をざっくり描きましょう。',
    '五つ目、親と、これからを話す。介護や住まい、お金のこと。元気なうちに聞いておくと安心です。',
    '六つ目、モノを減らす。使っていない物は思い切って手放す。家も頭もすっきりします。',
    '七つ目、新しいことを学ぶ。資格でも語学でもスマホでも。学ぶ習慣が六十代の選択肢を広げます。',
    'やっつめ、仕事以外の居場所をつくる。趣味や地域の活動で、肩書きなしで付き合える人を増やしましょう。',
    '九つ目、家族との時間を予定に入れる。旅行でも、月に一度のごはんでも。後回しにせずカレンダーへ。',
    '十個目、六十代のやりたいことのリストを書く。小さなことで大丈夫。書いた瞬間から人生が動き出します。',
    'まずは一つだけ、今日から始めてみませんか？参考になったら、保存といいねをお願いします。',
]
MIN_DUR = [4.0] + [5.0] * 10 + [5.5]   # シーンの最短長
TAIL = 0.40                            # ナレーション終了からシーン終了までの間
FPS = 30

# 字幕用テキスト(画面表示向けの表記)。render.html の SUBTITLES と同じ
SUBTITLES = [
    '50代のうちにやっておくべきこと10選。テンポよく紹介します！',
    '1つ目、人間ドックで体の棚卸し。病気が見つかりやすい年代です。年に1度はしっかり調べましょう。',
    '2つ目、筋トレで筋肉貯金。筋肉は使わないと減る一方。スクワットと早歩きから始めましょう。',
    '3つ目、歯のメンテナンス。歯を失うと食事も会話も変わります。3か月に1度はクリーニングを。',
    '4つ目、お金の見直し。年金、保険、資産をまとめて把握。60歳からの収支をざっくり描きましょう。',
    '5つ目、親と「これから」を話す。介護や住まい、お金のこと。元気なうちに聞いておくと安心です。',
    '6つ目、モノを減らす。使っていない物は思い切って手放す。家も頭もすっきりします。',
    '7つ目、新しいことを学ぶ。資格でも語学でもスマホでも。学ぶ習慣が60代の選択肢を広げます。',
    '8つ目、仕事以外の居場所をつくる。趣味や地域の活動で、肩書きなしで付き合える人を増やしましょう。',
    '9つ目、家族との時間を予定に入れる。旅行でも、月に1度のごはんでも。後回しにせずカレンダーへ。',
    '10個目、60代のやりたいことリストを書く。小さなことで大丈夫。書いた瞬間から人生が動き出します。',
    'まずは1つだけ、今日から始めてみませんか？参考になったら、保存といいねをお願いします。',
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class VoicevoxEngine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = os.environ.get('VOICEVOX_ORT') or next(iter(glob.glob('/home/user/vv/ort/**/libvoicevox_onnxruntime.so', recursive=True)), '')
        ort = Onnxruntime.load_once(filename=ort)
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.pitch_scale = 0.0
        q.intonation_scale = 1.15     # 少し抑揚を強めて明るく
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

class OpenJtalkEngine:
    def __init__(self):
        import pyopenjtalk
        self.tts = pyopenjtalk.tts
        print('engine: Open JTalk (fallback)')
    def __call__(self, text, speed):
        x, sr = self.tts(text, speed=speed)
        return x.astype(np.float32) / 32768.0, sr

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def _write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', path)

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'

def mux(src, dst):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', MIX,
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', dst], check=True)
    print('wrote', dst)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--mux':
        mux(sys.argv[2], sys.argv[3]); sys.exit(0)

    try:
        engine = VoicevoxEngine()
    except Exception as e:  # noqa
        print('VOICEVOX unavailable:', e)
        engine = OpenJtalkEngine()

    def synth(text, speed):
        x, sr = engine(text, speed)
        x = resample(x, sr)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx):
            x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
        return x

    SPEED = 1.28  # 話速(テンポよく、でも聞き取れる範囲)
    clips, durs = [], []
    for li, text in enumerate(SCRIPT):
        x = synth(text, SPEED)
        n = len(x); f = min(600, n // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        sec = n / SR
        d = max(MIN_DUR[li], LEAD + sec + TAIL)
        d = np.ceil(d * FPS) / FPS          # フレーム境界に揃える
        clips.append(x); durs.append(float(d))
        print(f'scene {li:2d}  voice {sec:4.2f}s  -> {d:4.2f}s  {text[:16]}…')
    starts = [float(sum(durs[:i])) for i in range(len(durs))]
    TOTAL = float(sum(durs))
    print(f'total {TOTAL:.2f}s')
    import json
    with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as fj:
        json.dump({'fps': FPS, 'durations': durs, 'starts': starts, 'total': TOTAL, 'subtitles': SUBTITLES}, fj, ensure_ascii=False, indent=1)
    print('wrote', os.path.join(OUT, 'timeline.json'))

    track = np.zeros(int(TOTAL * SR), dtype=np.float32)
    cues = []
    for li, (start, x) in enumerate(zip(starts, clips)):
        n = len(x)
        s = int((start + LEAD) * SR)
        e = min(s + n, len(track))
        track[s:e] += x[:e - s]
        cues.append((start + LEAD, start + LEAD + n / SR, SUBTITLES[li]))

    peak = np.max(np.abs(track)) or 1
    track = track / peak * 0.85
    _write(WAV, track)

    with open(SRT, 'w', encoding='utf-8') as fsrt:
        for i, (a, b, t) in enumerate(cues, 1):
            fsrt.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{t}\n\n')
    print('wrote', SRT)

    # ---------- BGM をダッキングしながらミックス ----------
    import bgm as bgm_mod
    music = bgm_mod.generate(TOTAL)
    _write(os.path.join(OUT, 'bgm.wav'), music)
    music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
    hop = SR // 20
    rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
    envl = np.zeros_like(rms)
    for i, v in enumerate(rms):
        prev = envl[i - 1] if i else 0.0
        envl[i] = max(v, prev * 0.9)       # リリース ≈ 0.5 秒
    envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
    speech = np.clip(envl / 0.12, 0, 1)
    BGM_SILENT, BGM_SPEECH = 0.42, 0.20   # 無音時 / 発話時の BGM ゲイン(線形)
    gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
    k = SR // 10
    gain = np.convolve(gain, np.ones(k) / k, mode='same')
    mixed = track + music * gain
    mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
    _write(MIX, mixed)
