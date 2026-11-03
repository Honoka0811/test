# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX: 青山龍星)をビート単位で合成し、シーンの尺をナレーションに合わせて決める。
出力: output/narration.wav, output/timing.json(render.html / capture.js が読む), output/subtitles_ja.srt
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ
  VOICEVOX_STYLE スタイルID(既定 13 = 青山龍星 ノーマル)
  SPEED          話速(既定 1.1)
"""
import sys, os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = float(os.environ.get('SPEED', '1.1'))
LEAD, GAP, TAIL = 0.7, 0.45, 1.0   # シーン冒頭の間 / ビート間の間 / シーン末尾の間

# 各シーン: (シーンID, [ (読み上げ用テキスト, 字幕テキスト or None, 表示する項目のインデックス一覧) ... ])
# 読み上げ用は英字略語をカタカナ、数値を漢数字にして VOICEVOX の読み間違いを避ける。
SCRIPT = [
    ('title', [
        ('次世代の戦争は、大量のドローンをエーアイで制御する消耗戦になる。そう考えたとき、勝敗を決めるのは何でしょうか。',
         '次世代の戦争は、大量のドローンをAIで制御する消耗戦になる。そう考えたとき、勝敗を決めるのは何でしょうか。', []),
    ]),
    ('premise', [
        ('ウクライナは二千二十五年、年間およそ四百万機のドローンを生産しました。ロシアはしゃへど型の長距離ドローンだけで、月に二千七百機前後を生産していると推定されています。',
         'ウクライナは2025年、年間およそ400万機のドローンを生産しました。ロシアはシャヘド型の長距離ドローンだけで、月に2,700機前後を生産していると推定されています。', [0, 1]),
        ('この動画では、半導体、電力、ドローン生産、宇宙インフラ、データと人材という五つの資源について、代替の利かないボトルネックを一つずつ確認します。',
         'この動画では、半導体、電力、ドローン生産、宇宙インフラ、データと人材という5つの資源について、代替の利かないボトルネックを一つずつ確認します。', [2]),
        ('数字はいずれも公開情報にもとづく概数です。出典は概要欄にまとめています。', None, []),
    ]),
    ('semi', [
        ('一つ目は半導体です。上流から見ていきます。設計ツールのイーディーエーは、シノプシス、ケイデンス、シーメンスの三社で世界市場の約七十四パーセントを占めます。二千二十五年五月、米国はこの三社の中国向け販売を止め、七月に解除しました。止められる、という事実が示された形です。',
         '一つ目は半導体です。上流から見ていきます。設計ツールのEDAは、Synopsys、Cadence、Siemensの3社で世界市場の約74%を占めます。2025年5月、米国はこの3社の中国向け販売を止め、7月に解除しました。止められる、という事実が示された形です。', [0]),
        ('露光装置では、イーユーブイ露光機を作れるのはエーエスエムエル一社だけです。中国への輸出は禁じられており、エスエムアイシーはディーユーブイの多重露光で七ナノメートル級にとどまっています。',
         '露光装置では、EUV露光機を作れるのはASML 1社だけです。中国への輸出は禁じられており、SMICはDUVの多重露光で7nm級にとどまっています。', [1]),
        ('三ナノメートル以下を量産できるのはティーエスエムシー、サムスン、インテルの三社で、比重は圧倒的にティーエスエムシーです。台湾への一点集中が構造的な弱点になります。',
         '3nm以下を量産できるのはTSMC、Samsung、Intelの3社で、比重は圧倒的にTSMCです。台湾への一点集中が構造的な弱点になります。', [2]),
        ('意外な律速が後工程です。エーアイ用ジーピーユーは、コワスという先端パッケージングとエイチビーエムメモリを必要とします。二千二十五年には上位四社がコワスとエイチビーエムの九割以上を消費しましたが、先端ロジックのウェハ生産に占める割合は約十二パーセントでした。つまり、ウェハではなくパッケージングが足りていません。',
         '意外な律速が後工程です。AI用GPUは、CoWoSという先端パッケージングとHBMメモリを必要とします。2025年には上位4社がCoWoSとHBMの9割以上を消費しましたが、先端ロジックのウェハ生産に占める割合は約12%でした。つまり、ウェハではなくパッケージングが足りていません。', [3]),
        ('材料も偏っています。フォトレジストは日本企業が六割から九割、シリコンウェハは信越化学とサムコの二社で約半分を占めます。',
         '材料も偏っています。フォトレジストは日本企業が6〜9割、シリコンウェハは信越化学とSUMCOの2社で約半分を占めます。', [4]),
        ('ただし、ドローン側の小型チップは二十八ナノメートル以上の成熟プロセスで足ります。ここは中国が自給できるため、先端ファブが効くのは訓練用の計算側です。',
         'ただし、ドローン側の小型チップは28nm以上の成熟プロセスで足ります。ここは中国が自給できるため、先端ファブが効くのは訓練用の計算側です。', [5]),
    ]),
    ('power', [
        ('二つ目は電力です。発電所を建てたくても、機械が来ません。大型ガスタービンはジーイー・バーノバ、シーメンス・エナジー、三菱重工の三社で、受注残はそれぞれ百十六ギガワット、六十九ギガワット、三十二ギガワットに達しています。納期は三年以上で、今注文しても納入は二千三十年代です。',
         '二つ目は電力です。発電所を建てたくても、機械が来ません。大型ガスタービンはGE Vernova、Siemens Energy、三菱重工の3社で、受注残はそれぞれ116GW、69GW、32GWに達しています。納期は3年以上で、今注文しても納入は2030年代です。', [0]),
        ('送電側も同じです。大型変圧器の平均納期は約百二十八週、二年半です。長いものは二百十週。材料の方向性電磁鋼板は、米国内では一社しか作っていません。',
         '送電側も同じです。大型変圧器の平均納期は約128週、2年半です。長いものは210週。材料の方向性電磁鋼板は、米国内では1社しか作っていません。', [1]),
        ('原子力では、ウラン濃縮能力の約四割をロシアが握っています。新型炉用の燃料ヘイルーは、米国のセントラス社が年間約九百キログラムを生産していますが、二千三十五年の需要見通しは五万キログラムです。',
         '原子力では、ウラン濃縮能力の約4割をロシアが握っています。新型炉用の燃料HALEUは、米国のCentrus社が年間約900kgを生産していますが、2035年の需要見通しは5万kgです。', [2]),
        ('急いで発電量を増やすなら再生可能エネルギーと蓄電ですが、太陽電池は中国が八割超、電池の正極材は九割、負極材は九十七パーセントを握ります。',
         '急いで発電量を増やすなら再生可能エネルギーと蓄電ですが、太陽電池は中国が8割超、電池の正極材は9割、負極材は97%を握ります。', [3]),
        ('そして電力は攻撃対象でもあります。ロシアがウクライナの送電網を狙い続けているように、消耗戦では総発電量よりも復旧の速さが効いてきます。', None, [4]),
    ]),
    ('drone', [
        ('三つ目はドローンの生産力です。完成機の組立は増やせます。問題は部品です。モーターに使うネオジム磁石は、二千二十四年時点で中国が世界の九十四パーセントを生産しています。二千二十五年四月の輸出規制では、翌月の磁石輸出が半減しました。',
         '三つ目はドローンの生産力です。完成機の組立は増やせます。問題は部品です。モーターに使うネオジム磁石は、2024年時点で中国が世界の94%を生産しています。2025年4月の輸出規制では、翌月の磁石輸出が半減しました。', [0]),
        ('電池セルも中国の寡占です。ウクライナの国産ドローンも、電池は輸入に頼っています。', None, [1]),
        ('安価な熱画像コアは中国メーカーが価格で圧倒し、炭素繊維は日本と中国に偏ります。兵器級の炭素繊維は輸出管理の対象です。', None, [2, 3]),
        ('見落とされがちなのが炸薬です。西側はニトロセルロース、ティーエヌティー、アールディーエックスの生産を冷戦後に縮小しました。米陸軍の評価では、アールディーエックスは今も国内で完全には生産できません。イーユーで大規模なティーエヌティー工場は一か所です。弾頭が機体より先に足りなくなります。',
         '見落とされがちなのが炸薬です。西側はニトロセルロース、TNT、RDXの生産を冷戦後に縮小しました。米陸軍の評価では、RDXは今も国内で完全には生産できません。EUで大規模なTNT工場は1か所です。弾頭が機体より先に足りなくなります。', [4]),
        ('新しい消耗品もあります。妨害に強い光ファイバー誘導ドローンは二千二十四年にロシアが先行し、一か月で千三百巻きのファイバーを調達したと報じられています。',
         '新しい消耗品もあります。妨害に強い光ファイバー誘導ドローンは2024年にロシアが先行し、1か月で1,300巻のファイバーを調達したと報じられています。', [5]),
    ]),
    ('space', [
        ('四つ目は宇宙インフラです。ウクライナの海上ドローン、シーベイビーやマグラは、スターリンク経由で遠隔操縦され、黒海艦隊に実害を与えました。二千二十六年には、ロシアも密輸したスターリンク端末を自国の海上ドローンに載せていることが確認されています。',
         '四つ目は宇宙インフラです。ウクライナの海上ドローン、Sea BabyやMaguraは、スターリンク経由で遠隔操縦され、黒海艦隊に実害を与えました。2026年には、ロシアも密輸したスターリンク端末を自国の海上ドローンに載せていることが確認されています。', [0]),
        ('ただし小型機には載りません。小型端末のスターリンク・ミニでも重さ約一キログラム、消費電力は二十五から四十ワットです。機体全体で一キログラムのエフピーブイドローンには搭載できません。雲と前線をつなぐのは、中型機以上の役割になります。',
         'ただし小型機には載りません。小型端末のStarlink Miniでも重さ約1kg、消費電力は25〜40Wです。機体全体で1kgのFPVドローンには搭載できません。雲と前線をつなぐのは、中型機以上の役割になります。', [1]),
        ('衛星網を自前で持てるかは、打ち上げ能力で決まります。二千二十五年、スペースエックスは世界の軌道投入質量の八割以上、打ち上げ回数の約半分を占めました。',
         '衛星網を自前で持てるかは、打ち上げ能力で決まります。2025年、SpaceXは世界の軌道投入質量の8割以上、打ち上げ回数の約半分を占めました。', [2]),
        ('中国はセンパンとコクモウという二つの低軌道網を急いでいますが、二千二十六年半ばの衛星数はそれぞれ二百四十機と百九十機程度で、スターリンクのすうじゅうぶんのいちです。',
         '中国は千帆と国網という2つの低軌道網を急いでいますが、2026年半ばの衛星数はそれぞれ240機と190機程度で、スターリンクの数十分の一です。', [3]),
        ('そして、誰が止められるかです。スターリンクは米国の一企業が握っており、二千二十二年にはクリミア沖で通信を有効にしなかった前例があります。米国以外にとっては、他国依存の資源です。',
         'そして、誰が止められるかです。スターリンクは米国の一企業が握っており、2022年にはクリミア沖で通信を有効にしなかった前例があります。米国以外にとっては、他国依存の資源です。', [4]),
    ]),
    ('data', [
        ('五つ目はデータと人材です。前線の映像と撃墜記録を集め、ラベルを付け、数週間でモデルを更新して配布できるか。同じチップでも、この仕組みの有無で価値が変わります。', None, [0, 1]),
        ('ウクライナが戦場映像を国家単位で収集しているのはこのためです。これは物理的な資源ではなく、組織と制度のボトルネックです。', None, [2]),
    ]),
    ('summary', [
        ('まとめます。米国の急所は電力機器と部品供給網。中国の急所はイーユーブイと先端ファブと打ち上げ能力。欧州と日本の急所は打ち上げとエーアイ計算基盤。ウクライナ型の中堅国の急所は電池と磁石と炸薬です。',
         'まとめます。米国の急所は電力機器と部品供給網。中国の急所はEUVと先端ファブと打ち上げ能力。欧州と日本の急所は打ち上げとAI計算基盤。ウクライナ型の中堅国の急所は電池と磁石と炸薬です。', [0, 1, 2, 3]),
        ('最後に一つ。これらの資源が勝敗を決めるのは、核抑止が働く天井の下での話です。大国同士では消耗戦が本格化する前に抑制がかかります。資源の競争は、その天井の下で続いていきます。', None, [4]),
    ]),
    ('end', []),
]
END_DUR = 7.0

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class VoicevoxEngine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '13'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, self.style)
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
    x, sr = engine(text, SPEED)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

# ---------- 合成と配置 ----------
clips = []        # (開始秒, 波形)
timing = {'scenes': []}
t = 0.0
for sid, beats in SCRIPT:
    scene = {'id': sid, 'start': round(t, 3), 'beats': []}
    if sid == 'end':
        t += END_DUR
    else:
        bt = t + (1.2 if sid == 'title' else LEAD)
        for k, (tts, sub, reveal) in enumerate(beats):
            x = synth(tts)
            sec = len(x) / SR
            clips.append((bt, x))
            scene['beats'].append({'start': round(bt, 3), 'end': round(bt + sec, 3), 'sub': sub or tts, 'reveal': reveal})
            print(f'{bt:6.1f}s  {sec:5.1f}s  [{sid}] {(sub or tts)[:22]}…')
            bt += sec + GAP
        t = bt - GAP + TAIL + (0.6 if sid == 'title' else 0)
    scene['dur'] = round(t - scene['start'], 3)
    timing['scenes'].append(scene)
TOTAL = round(t, 3)
timing['total'] = TOTAL
print(f'total {TOTAL:.1f}s')

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
os.makedirs(OUT, exist_ok=True)
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
with open(os.path.join(OUT, 'timing.json'), 'w', encoding='utf-8') as f:
    json.dump(timing, f, ensure_ascii=False, indent=1)

def _ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 1
    for sc in timing['scenes']:
        for b in sc['beats']:
            f.write(f"{i}\n{_ts(b['start'])} --> {_ts(min(b['end'] + 0.3, TOTAL))}\n{b['sub']}\n\n"); i += 1
print('wrote', OUT)
