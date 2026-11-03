# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX: 青山龍星)を文ごとに合成し、
シーン尺・字幕タイミング(output/timing.json, output/subtitles_ja.srt)と
BGM(bgm.py)をダッキングしたミックス音声(output/mix.wav)を書き出す。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(15.vvm = 青山龍星)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 13 = 青山龍星 ノーマル)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.12'))
LEAD, TAIL = 0.7, 1.0      # シーン頭/尻の無音
GAP = 0.28                 # 文と文の間
STYLE = int(os.environ.get('VOICEVOX_STYLE', '13'))

# (シーンID, 見出し, [(読み上げ文, 字幕文), ...])
# 読み上げ文は漢数字・読み仮名寄り、字幕は表示用
SCENES = [
    ('hook', 'ミッドウェー海戦 日本はどうすれば勝てたか', [
        ('千九百四十二年六月、ミッドウェー。日本海軍は主力空母四隻を、わずか一日で失いました。', '1942年6月、ミッドウェー。日本海軍は主力空母4隻を、わずか1日で失いました。'),
        ('しかしこの戦い、日本には勝ち筋がありました。', 'しかしこの戦い、日本には勝ち筋がありました。'),
        ('今日は、その条件を五つに絞って解説します。', '今日は、その条件を5つに絞って解説します。'),
    ]),
    ('forces', '両軍の戦力', [
        ('まず戦力です。日本は南雲機動部隊の空母四隻、赤城、加賀、蒼龍、飛龍。', 'まず戦力です。日本は南雲機動部隊の空母4隻、赤城・加賀・蒼龍・飛龍。'),
        ('対する米軍は、エンタープライズ、ホーネット、そして珊瑚海で損傷したヨークタウンの三隻。', '対する米軍は、エンタープライズ、ホーネット、そして珊瑚海で損傷したヨークタウンの3隻。'),
        ('さらにミッドウェー島の航空隊が加わります。数の上では、日本がやや優勢でした。', 'さらにミッドウェー島の航空隊が加わります。数の上では、日本がやや優勢でした。'),
    ]),
    ('code', '条件① 暗号を更新する', [
        ('条件その一、暗号を更新すること。', '条件①　暗号を更新すること。'),
        ('米軍は日本海軍の暗号、ジェイエヌにじゅうごを部分的に解読していました。', '米軍は日本海軍の暗号 JN-25 を部分的に解読していました。'),
        ('攻撃目標はミッドウェー、時期は六月上旬。ここまで読まれていたのです。', '攻撃目標はミッドウェー、時期は6月上旬。ここまで読まれていたのです。'),
        ('暗号書の更新は五月末の予定でしたが、作戦準備の都合で六月に延期されました。', '暗号書の更新は5月末の予定でしたが、作戦準備の都合で6月に延期されました。'),
        ('もし予定通り更新されていれば、米空母の待ち伏せ自体が成立しません。', 'もし予定通り更新されていれば、米空母の待ち伏せ自体が成立しません。'),
    ]),
    ('concentrate', '条件② 戦力を分散しない', [
        ('条件その二、戦力を分散しないこと。', '条件②　戦力を分散しないこと。'),
        ('日本は同じタイミングで、アリューシャンにも空母二隻を送りました。', '日本は同じタイミングで、アリューシャンにも空母2隻を送りました。'),
        ('さらに大和を含む戦艦部隊は、空母の数百キロ後方。決戦の場にいたのは、空母四隻だけです。', 'さらに大和を含む戦艦部隊は、空母の数百キロ後方。決戦の場にいたのは、空母4隻だけです。'),
        ('珊瑚海で損傷した瑞鶴も、修理と搭乗員の補充を急げば間に合った可能性があります。', '珊瑚海で損傷した瑞鶴も、修理と搭乗員の補充を急げば間に合った可能性があります。'),
        ('全戦力を一か所に集めれば、防空も索敵も倍になります。', '全戦力を1か所に集めれば、防空も索敵も倍になります。'),
    ]),
    ('search', '条件③ 索敵を厚くする', [
        ('条件その三、索敵を厚くすること。', '条件③　索敵を厚くすること。'),
        ('当日朝、日本が出した索敵機はわずか七機。', '当日朝、日本が出した索敵機はわずか7機。'),
        ('しかも重巡利根の四号機は、カタパルトの不調で発進が三十分遅れました。', 'しかも重巡「利根」の4号機は、カタパルトの不調で発進が30分遅れました。'),
        ('皮肉にも、米空母がいたのは、その四号機の担当海域です。', '皮肉にも、米空母がいたのは、その4号機の担当海域です。'),
        ('索敵機を倍に増やし、二段構えにしていれば、米空母の発見は一時間以上早まった可能性があります。', '索敵機を倍に増やし、二段構えにしていれば、米空母の発見は1時間以上早まった可能性があります。'),
    ]),
    ('launch', '条件④ 積み替えずに今すぐ飛ばす', [
        ('条件その四、積み替えずに、今すぐ飛ばすこと。', '条件④　積み替えずに、今すぐ飛ばすこと。'),
        ('七時二十八分、利根四号機が敵艦隊発見を報告。', '7時28分、利根4号機が敵艦隊発見を報告。'),
        ('しかし南雲司令部はすでに、第二次攻撃隊の魚雷を、陸用爆弾に積み替えていました。', 'しかし南雲司令部はすでに、第二次攻撃隊の魚雷を、陸用爆弾に積み替えていました。'),
        ('空母発見で、今度は魚雷に戻す。この往復に、時間を奪われます。', '空母発見で、今度は魚雷に戻す。この往復に、時間を奪われます。'),
        ('第二航空戦隊の山口多聞少将は、現装備のまま直ちに発進の要ありと認む、と意見具申しました。', '第二航空戦隊の山口多聞少将は「現装備のまま直ちに発進の要ありと認む」と意見具申しました。'),
        ('しかしこれは退けられ、十時二十分。', 'しかしこれは退けられ、10時20分。'),
        ('米急降下爆撃隊が、燃料と爆弾を満載した甲板に突入。', '米急降下爆撃隊が、燃料と爆弾を満載した甲板に突入。'),
        ('わずか五分で、赤城、加賀、蒼龍が炎上しました。', 'わずか5分で、赤城・加賀・蒼龍が炎上しました。'),
    ]),
    ('cap', '条件⑤ 頭上を空にしない', [
        ('条件その五、頭上を空にしないこと。', '条件⑤　頭上を空にしないこと。'),
        ('直前に米雷撃隊が低空から襲いかかり、直衛の零戦はそれを追って、海面近くまで降りていました。', '直前に米雷撃隊が低空から襲いかかり、直衛の零戦はそれを追って、海面近くまで降りていました。'),
        ('そのため高高度はがら空き。急降下爆撃機は、ほぼ無抵抗で突入できたのです。', 'そのため高高度はがら空き。急降下爆撃機は、ほぼ無抵抗で突入できたのです。'),
        ('高高度に警戒隊を常に残す運用なら、少なくとも被害は減らせました。', '高高度に警戒隊を常に残す運用なら、少なくとも被害は減らせました。'),
    ]),
    ('war', 'それでも戦争には勝てない', [
        ('では、この五つが揃って日本が勝ったら、戦争はどうなったか。', 'では、この5つが揃って日本が勝ったら、戦争はどうなったか。'),
        ('結論は、戦いには勝てても、戦争には勝てません。', '結論は、戦いには勝てても、戦争には勝てません。'),
        ('米国はこの時点で、エセックス級の大型空母を十隻以上建造中。', '米国はこの時点で、エセックス級の大型空母を10隻以上建造中。'),
        ('千九百四十三年以降、戦力差は一方的に開きます。', '1943年以降、戦力差は一方的に開きます。'),
        ('日本が得られる最大の成果は、米軍の反攻を一年遅らせること。それを講和につなげられるかは、政治の問題でした。', '日本が得られる最大の成果は、米軍の反攻を1年遅らせること。それを講和につなげられるかは、政治の問題でした。'),
    ]),
    ('summary', 'まとめ', [
        ('まとめます。暗号の更新と兵力集中で待ち伏せを避け、索敵強化と即時発進で先手を取る。', 'まとめます。暗号の更新と兵力集中で待ち伏せを避け、索敵強化と即時発進で先手を取る。'),
        ('これで、ミッドウェーの勝利は十分に現実的でした。', 'これで、ミッドウェーの勝利は十分に現実的でした。'),
        ('ただし勝てたのは、戦いであって、戦争ではなかった。', 'ただし勝てたのは「戦い」であって、「戦争」ではなかった。'),
        ('ご視聴ありがとうございました。', 'ご視聴ありがとうございました。'),
    ]),
]

def _dict_dir():
    return os.environ.get('VOICEVOX_DICT', '/home/user/vv/dict/open_jtalk_dic_utf_8-1.11')

class VoicevoxEngine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/dl'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == STYLE)
        print('engine: VOICEVOX', name)
    def __call__(self, text):
        q = self.synth.create_audio_query(text, STYLE)
        q.speed_scale = SPEED
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.08
        wav = self.synth.synthesis(q, STYLE)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

engine = VoicevoxEngine()

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def synth(text):
    x, sr = engine(text)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    n = len(x); f = min(400, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

# ---------- 合成とタイミング ----------
clips = []   # (scene index, start, wav)
timing = {'fps': 30, 'scenes': []}
t = 0.0
for si, (sid, title, sents) in enumerate(SCENES):
    sc_start = t
    t += LEAD
    subs = []
    for spoken, shown in sents:
        x = synth(spoken)
        dur = len(x) / SR
        clips.append((t, x))
        subs.append({'start': round(t, 3), 'end': round(t + dur, 3), 'text': shown})
        t += dur + GAP
    t += TAIL - GAP
    timing['scenes'].append({'id': sid, 'title': title, 'start': round(sc_start, 3), 'dur': round(t - sc_start, 3), 'subs': subs})
    print(f'{sc_start:6.1f}s  {t - sc_start:5.1f}s  {title}')
TOTAL = round(t, 2)
timing['duration'] = TOTAL
print('total', TOTAL, 's')

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for start, x in clips:
    s = int(start * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85

def wwav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
wwav(os.path.join(OUT, 'narration.wav'), track)

with open(os.path.join(OUT, 'timing.json'), 'w', encoding='utf-8') as f:
    json.dump(timing, f, ensure_ascii=False, indent=1)

def _ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 1
    for sc in timing['scenes']:
        for sb in sc['subs']:
            f.write(f"{i}\n{_ts(sb['start'])} --> {_ts(min(sb['end'] + 0.25, TOTAL))}\n{sb['text']}\n\n"); i += 1

# ---------- BGM をダッキングしながらミックス ----------
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL + 2)[:len(track)]
music = np.pad(music, (0, max(0, len(track) - len(music))))
# 末尾フェードアウト
fo = int(2.5 * SR); music[-fo:] *= np.linspace(1, 0, fo)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.17
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
wwav(os.path.join(OUT, 'bgm.wav'), music * BGM_SILENT)
wwav(os.path.join(OUT, 'mix.wav'), mixed)
print('wrote output/narration.wav output/timing.json output/subtitles_ja.srt output/mix.wav')
