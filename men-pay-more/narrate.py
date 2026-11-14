# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:青山龍星)を合成し、その長さからシーン尺を決めて output/timings.json と字幕SRTを書き出す。
mix モードでは BGM をダッキングしながらミックスし、映像と合成する。
使い方:
  python3 narrate.py voice              # ナレーション合成 → timings.json / narration.wav / subtitles_ja.srt
  python3 narrate.py mix [入力mp4] [出力mp4]  # BGM ミックス + 映像と合成
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 13 = 青山龍星 ノーマル)
"""
import sys, os, io, wave, glob, json, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
LEAD = 0.35   # シーン開始 → 発話開始
TAIL = 0.65   # 発話終了 → 次のシーン
SPEED = 1.2

# (シーンID, 読み上げ原稿, 字幕)
SCRIPT = [
    ('title',  'デート代や食事代、男性が多く払うべきなのか。よく挙げられる理由を、四つ紹介します。',
               'デート代や食事代、男性が多く払うべき？よく挙げられる理由を4つ紹介します。'),
    ('wage',   '理由その一、収入の差。日本の女性の平均賃金は、男性のおよそ七十六パーセント。月に九万円ほどの差があります。',
               '理由①　収入の差。日本の女性の平均賃金は男性の約76%。月に約9万円の差があります。'),
    ('beauty', '理由その二、身だしなみのコスト。化粧品や美容院、服など、女性は見た目にかかるお金が多くなりがちです。',
               '理由②　身だしなみのコスト。化粧品や美容院、服など、女性は見た目にかかるお金が多くなりがちです。'),
    ('life',   '理由その三、ライフイベントの影響。出産や育児をきっかけに、女性は正社員の割合が下がり、収入が減りやすい傾向があります。',
               '理由③　ライフイベントの影響。出産や育児をきっかけに正社員の割合が下がり、収入が減りやすい傾向があります。'),
    ('safety', '理由その四、安全のためのお金。夜道を避けるタクシー代や、オートロックの部屋など、防犯にかかる出費もあります。',
               '理由④　安全のためのお金。夜道を避けるタクシー代やオートロックの部屋など、防犯にかかる出費もあります。'),
    ('wrap',   'とはいえ、正解はカップルそれぞれ。収入に差がなければ、割り勘も自然です。大切なのは、二人が納得できる払い方を話し合うことです。',
               'とはいえ、正解はカップルそれぞれ。収入に差がなければ割り勘も自然。大切なのは、二人が納得できる払い方を話し合うこと。'),
    ('end',    'あなたは、どう思いますか？',
               'あなたはどう思いますか？'),
]
END_HOLD = 2.6  # 最後のカードを表示し続ける秒数

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return pyopenjtalk.OPEN_JTALK_DICT_DIR.decode()

def make_engine():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
        '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
    synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
        with VoiceModelFile.open(f) as m:
            synth.load_voice_model(m)
    style = int(os.environ.get('VOICEVOX_STYLE', '13'))
    name = next((c.name + '/' + st.name) for c in synth.metas() for st in c.styles if st.id == style)
    print('engine: VOICEVOX', name)
    def tts(text):
        q = synth.create_audio_query(text, style)
        q.speed_scale = SPEED
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(synth.synthesis(q, style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
        f = min(600, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x
    return tts

def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

def _ts(t):
    m = int(t // 60); s = t % 60
    return f'00:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'

def voice():
    tts = make_engine()
    clips, scenes, t = [], [], 0.0
    for sid, text, sub in SCRIPT:
        x = tts(text)
        sec = len(x) / SR
        dur = LEAD + sec + (END_HOLD if sid == 'end' else TAIL)
        scenes.append({'id': sid, 'start': round(t, 3), 'dur': round(dur, 3),
                       'speechStart': round(t + LEAD, 3), 'speechEnd': round(t + LEAD + sec, 3), 'sub': sub})
        clips.append((t + LEAD, x))
        print(f'{t:5.2f}s  {sid:7s} speech {sec:4.2f}s  scene {dur:4.2f}s')
        t += dur
    total = round(t, 2)
    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for st, x in clips:
        s = int(st * SR); track[s:s + len(x)] += x
    track = track[:int(total * SR)]
    track = track / (np.max(np.abs(track)) or 1) * 0.85
    write_wav(os.path.join(OUT, 'narration.wav'), track)
    with open(os.path.join(OUT, 'timings.json'), 'w', encoding='utf-8') as f:
        json.dump({'total': total, 'scenes': scenes}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, s in enumerate(scenes, 1):
            f.write(f"{i}\n{_ts(s['speechStart'])} --> {_ts(min(s['speechEnd'] + 0.3, total))}\n{s['sub']}\n\n")
    print('total', total, 's → wrote narration.wav / timings.json / subtitles_ja.srt')

def mix(src, dst):
    import bgm as bgm_mod
    with wave.open(os.path.join(OUT, 'narration.wav')) as w:
        track = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    total = len(track) / SR
    music = bgm_mod.generate(total)
    music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
    write_wav(os.path.join(OUT, 'bgm.wav'), music)
    # ダッキング: ナレーションの包絡に応じて BGM を下げる
    hop = SR // 20
    rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(rms)
    for i, v in enumerate(rms):
        env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
    env = np.pad(np.repeat(env, hop), (0, len(track) - len(rms) * hop))
    speech = np.clip(env / 0.12, 0, 1)
    gain = 0.42 - (0.42 - 0.17) * speech
    k = SR // 10
    gain = np.convolve(gain, np.ones(k) / k, mode='same')
    mixed = track + music * gain
    mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
    write_wav(os.path.join(OUT, 'mix.wav'), mixed)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', os.path.join(OUT, 'mix.wav'),
                    '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ac', '2', '-ar', '48000',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
    print('wrote', dst)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'voice'
    if mode == 'voice':
        voice()
    else:
        mix(sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'video_silent.mp4'),
            sys.argv[3] if len(sys.argv) > 3 else os.path.join(OUT, 'men_pay_more.mp4'))
