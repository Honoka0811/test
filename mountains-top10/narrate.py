# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、シーン尺・字幕・BGMミックスを作る。
  python3 narrate.py            … ナレーション合成 → output/timing.json, narration.wav, subtitles_ja.srt, mix.wav
  python3 narrate.py --no-voice … ナレーション無しで BGM だけの mix.wav を作る(scenes.json の既定尺。プレビュー用)
各シーンの尺は「ナレーション長 + 前後の間」に自動で合わせる(短すぎる場合は最低尺を確保)。
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま, 6 = ツンツン)
  VOICEVOX_SPEED 話速(既定 1.22)
"""
import sys, os, io, json, wave, glob
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = bgm_mod.SR
LEAD, TAIL = 0.40, 0.55          # シーン頭からナレーション開始まで / 読み終わりから次シーンまで
MIN_DUR = {'intro': 4.0, 'outro': 5.5, 'fuji': 7.0}
MIN_DEFAULT = 5.0                 # 文字アニメーションが落ち着くのに必要な最低尺

data = json.load(open(os.path.join(HERE, 'scenes.json'), encoding='utf-8'))
scenes = data['scenes']
no_voice = '--no-voice' in sys.argv

class Voicevox:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        vv = os.path.expanduser('/home/user/vv')
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
              os.path.join(vv, 'ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so')))
        self.synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', os.path.join(vv, 'dict/open_jtalk_dic_utf_8-1.11'))))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', os.path.join(vv, 'vvms')), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        self.speed = float(os.environ.get('VOICEVOX_SPEED', '1.22'))
        name = next(c.name + '/' + s.name for c in self.synth.metas() for s in c.styles if s.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = self.speed
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(self.synth.synthesis(q, self.style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx): x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
        f = min(600, len(x) // 4); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x

# ---------- ナレーション合成と尺の決定 ----------
clips, timing = [], {}
if not no_voice:
    tts = Voicevox()
    for s in scenes:
        x = tts(s['read'])
        dur = max(MIN_DUR.get(s['id'], MIN_DEFAULT), LEAD + len(x) / SR + TAIL)
        timing[s['id']] = round(dur, 3)
        clips.append(x)
        print(f"{s['id']:10s} voice {len(x)/SR:4.1f}s  scene {dur:4.1f}s")
    json.dump(timing, open(os.path.join(OUT, 'timing.json'), 'w'), indent=1)
else:
    timing = {s['id']: s['dur'] for s in scenes}
starts, t = [], 0.0
for s in scenes: starts.append(t); t += timing[s['id']]
TOTAL = t
print(f'total {TOTAL:.2f}s')

voice = np.zeros(int(TOTAL * SR), np.float32)
if clips:
    cues = []
    for s, st, x in zip(scenes, starts, clips):
        a = int((st + LEAD) * SR); e = min(a + len(x), len(voice)); voice[a:e] += x[:e - a]
        cues.append((st + LEAD, st + LEAD + len(x) / SR, s['sub']))
    voice = voice / (np.max(np.abs(voice)) or 1) * 0.85
    bgm_mod.write(os.path.join(OUT, 'narration.wav'), voice)
    def ts(v):
        return f'{int(v//3600):02d}:{int(v%3600//60):02d}:{int(v%60):02d},{int(round((v-int(v))*1000)):03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f'{i}\n{ts(a)} --> {ts(min(b + .3, TOTAL))}\n{txt}\n\n')

# ---------- BGM をダッキングしながらミックス ----------
music = bgm_mod.generate(TOTAL, intro=timing['intro'])
music = np.pad(music, (0, max(0, len(voice) - len(music))))[:len(voice)]
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms): envl[i] = max(v, (envl[i - 1] if i else 0) * 0.9)
envl = np.pad(np.repeat(envl, hop), (0, len(voice) - len(rms) * hop))
speech = np.clip(envl / 0.1, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.55, 0.22
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
mixed = voice + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
bgm_mod.write(os.path.join(OUT, 'bgm.wav'), music)
bgm_mod.write(os.path.join(OUT, 'mix.wav'), mixed)
print('wrote output/mix.wav')
