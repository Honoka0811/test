# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、シーン尺を決めて timeline.js / narration.wav / 字幕SRT を書き出す。
その後 render.html の映像(capture.js)ができていれば、BGM をダッキングしながらミックスして完成 mp4 を作る。
使い方:
  python3 narrate.py           # 音声 + timeline.js を作る(映像レンダリング前に実行)
  python3 narrate.py mux       # 映像 output/video.mp4 に音声を合成して output/bucket_list_10.mp4 を作る
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import sys, os, io, wave, glob, json, subprocess
import numpy as np
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
LEAD = 0.30      # シーン開始から発話開始まで
TAIL = 0.55      # 発話終了から次シーンまで
SPEED = 1.22

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

def make_engine():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
        '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
    synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
        with VoiceModelFile.open(f) as m:
            synth.load_voice_model(m)
    style = int(os.environ.get('VOICEVOX_STYLE', '2'))
    name = next((c.name + '/' + st.name) for c in synth.metas() for st in c.styles if st.id == style)
    print('engine: VOICEVOX', name)
    def tts(text, speed, pitch=0.0, intonation=1.15):
        q = synth.create_audio_query(text, style)
        q.speed_scale = speed; q.pitch_scale = pitch; q.intonation_scale = intonation
        q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.1
        wav = synth.synthesis(q, style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx): x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
        f = min(600, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x
    return tts

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'

def build():
    tts = make_engine()
    clips, timeline, t = [], [], 0.0
    for sc in SCENES:
        x = tts(sc['say'], SPEED, intonation=1.25 if sc['rank'] in (None, 1, 3) else 1.15)
        sec = len(x) / SR
        dur = max(4.0, LEAD + sec + TAIL)
        if sc['id'] == 'outro': dur += 1.2   # 最後は少し余韻を残す
        clips.append((t + LEAD, x))
        timeline.append(dict(id=sc['id'], rank=sc['rank'], title=sc['title'], sub=sc['sub'],
                             start=round(t, 3), dur=round(dur, 3),
                             speech=[round(t + LEAD, 3), round(t + LEAD + sec, 3)]))
        print(f"{t:6.2f}s  dur={dur:4.2f}  speech={sec:4.2f}  {sc['say'][:20]}…")
        t += dur
    total = round(t, 3)
    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for s, x in clips:
        i = int(s * SR); track[i:i + len(x)] += x
    track = track[:int(total * SR)]
    track = track / (np.max(np.abs(track)) or 1) * 0.85
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('// narrate.py が自動生成。手で編集しない\n')
        f.write('window.TIMELINE = ' + json.dumps(dict(total=total, scenes=timeline), ensure_ascii=False, indent=1) + ';\n')
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, sc in enumerate(timeline, 1):
            a, b = sc['speech']
            f.write(f"{i}\n{_ts(a)} --> {_ts(min(b + 0.3, total))}\n{sc['sub']}\n\n")
    print('total', total, 's')

def sfx(n):
    """シーン切り替えの効果音(ホワイトノイズのシュッ + ベルのキラン)"""
    tl = json.loads(open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read().split('=', 1)[1].rstrip().rstrip(';'))
    rng = np.random.default_rng(1)
    out = np.zeros(n, dtype=np.float32)
    m = int(0.35 * SR); t = np.arange(m) / SR
    for sc in tl['scenes'][1:]:
        nz = rng.standard_normal(m).astype(np.float32)
        nz = nz - np.convolve(nz, np.ones(8) / 8, mode='same')
        whoosh = nz * np.sin(np.pi * t / t[-1]) ** 2 * 0.5
        f = 1568 if sc['rank'] and sc['rank'] <= 3 else 1319
        chime = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.12)
        sig = whoosh + 0.6 * np.roll(chime, int(0.12 * SR)) * (t > 0.12)
        i = int(max(0, sc['start'] - 0.12) * SR); e = min(n, i + m)
        out[i:e] += sig[:e - i]
    return out

def mux():
    import bgm as bgm_mod
    with wave.open(os.path.join(OUT, 'narration.wav')) as w:
        track = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    music = bgm_mod.generate(len(track) / SR)[:len(track)]
    music = np.pad(music, (0, len(track) - len(music)))
    with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((music * 32767).astype(np.int16).tobytes())
    # ダッキング: ナレーション中は BGM を下げる
    hop = SR // 20
    rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(rms)
    for i, v in enumerate(rms):
        env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
    env = np.pad(np.repeat(env, hop), (0, len(track) - len(rms) * hop))
    speech = np.clip(env / 0.1, 0, 1)
    gain = 0.42 - (0.42 - 0.17) * speech
    k = SR // 10
    gain = np.convolve(gain, np.ones(k) / k, mode='same')
    mixed = track + music * gain + 0.22 * sfx(len(track))
    mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
    mix_path = os.path.join(OUT, 'mix.wav')
    with wave.open(mix_path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mixed * 32767).astype(np.int16).tobytes())
    src, dst = os.path.join(OUT, 'video.mp4'), os.path.join(OUT, 'bucket_list_10.mp4')
    # -14 LUFS(YouTube / TikTok の基準付近)に正規化し、ステレオ AAC で書き出す
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', mix_path, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ac', '2', '-ar', '48000',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
    os.remove(mix_path)
    print('wrote', dst)

if __name__ == '__main__':
    mux() if sys.argv[1:] == ['mux'] else build()
