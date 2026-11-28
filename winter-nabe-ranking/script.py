# -*- coding: utf-8 -*-
"""台本 → VOICEVOX で掛け合い音声を合成し、映像・効果音が参照するタイムラインを書き出す。

出力:
  build/voice.wav        掛け合いナレーション(48kHz mono)
  build/timeline.json    シーン開始時刻・セリフ・演出イベント(audio.py が参照)
  build/timeline.js      同じ内容を window.TIMELINE として(render.html が参照)
  output/subtitles_ja.srt 字幕

環境変数(省略時は /home/user/vv 以下):
  VOICEVOX_ORT  libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVM  0.vvm(四国めたん・ずんだもん)のパス
  VOICEVOX_DICT Open JTalk 辞書ディレクトリ
"""
import os, io, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build'); OUT = os.path.join(HERE, 'output')
os.makedirs(BUILD, exist_ok=True); os.makedirs(OUT, exist_ok=True)
SR = 48000
FPS = 30

VV = '/home/user/vv'
ORT = os.environ.get('VOICEVOX_ORT', f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so')
VVM = os.environ.get('VOICEVOX_VVM', f'{VV}/vvms/0.vvm')
DICT = os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')

# 話者: VOICEVOX スタイルID と声の味付け
SPEAKERS = {
    'metan': dict(style=2, name='四国めたん', speed=1.13, pitch=0.0, intonation=1.30),   # 司会
    'zunda': dict(style=3, name='ずんだもん', speed=1.12, pitch=0.02, intonation=1.40),  # はしゃぎ役
}

# ランキング(独断と偏見)。映像側の具材・色は render.html の DISH_ART にある
DISHES = {
    'tonyu':  dict(rank=5, name='豆乳鍋',   poka=3, shime='チーズリゾット', pops=['まろやか〜', 'お肌ツヤツヤ']),
    'motsu':  dict(rank=4, name='もつ鍋',   poka=4, shime='ちゃんぽん麺',   pops=['ぷりっぷり！', 'にんにくパワー']),
    'yose':   dict(rank=3, name='寄せ鍋',   poka=4, shime='雑炊',           pops=['具だくさん！', 'なんでもアリ']),
    'suki':   dict(rank=2, name='すき焼き', poka=3, shime='うどん',         pops=['ジュワ〜ッ', 'ごはん泥棒']),
    'kimchi': dict(rank=1, name='キムチ鍋', poka=5, shime='ラーメン＋チーズ', pops=['ピリ辛！！', 'ポッカポカ']),
}

# セリフ: (話者, 表示テキスト, [(読み上げテキスト, パーツ名), ...])
# 1 セリフを複数パーツに分けて合成すると、各パーツの開始時刻を演出に使える(例: 料理名を言った瞬間に名前を出す)
def L(sp, text, *parts):
    parts = parts or [(text, None)]
    return dict(speaker=sp, text=text, parts=[dict(say=s, key=k) for s, k in parts])

SCENES = [
    dict(id='intro', kind='intro', pre=0.30, gap=0.20, post=0.35, lines=[
        L('zunda', 'さむ〜い！|こんな日はお鍋に限るのだ！', ('さむーい！', 'samui'), ('こんな日は、お鍋に限るのだ！', None)),
        L('metan', '冬に食べたいお鍋ランキング！|いくわよ！', ('冬に食べたい、お鍋ランキング！', 'title'), ('いくわよ！', 'go')),
    ]),
    dict(id='r5', kind='rank', dish='tonyu', pre=0.32, gap=0.22, post=0.55, lines=[
        L('metan', '第5位！豆乳鍋！', ('だいごい！', 'rank'), ('とうにゅうなべ！', 'name')),
        L('zunda', 'まろやか〜！シメの|チーズリゾットが最高なのだ！', ('まろやかー！', 'pop1'), ('シメのチーズリゾットが、最高なのだ！', 'shime')),
    ]),
    dict(id='r4', kind='rank', dish='motsu', pre=0.32, gap=0.22, post=0.55, lines=[
        L('metan', '第4位！もつ鍋！', ('だいよんい！', 'rank'), ('もつなべ！', 'name')),
        L('zunda', 'ぷりっぷりのモツに、|ニラとにんにく！|元気モリモリなのだ！',
          ('ぷりっぷりのモツに、', 'pop1'), ('ニラとにんにく！', 'pop2'), ('元気モリモリなのだ！', None)),
    ]),
    dict(id='r3', kind='rank', dish='yose', pre=0.32, gap=0.22, post=0.55, lines=[
        L('metan', '第3位！寄せ鍋！', ('だいさんい！', 'rank'), ('よせなべ！', 'name')),
        L('zunda', '好きな具を、|ぜ〜んぶ入れちゃうのだ！', ('好きな具を、ぜーんぶ入れちゃうのだ！', 'pop1')),
        L('metan', 'シメの雑炊まで、|ぬかりなしよ！', ('シメの雑炊まで、ぬかりなしよ！', 'shime')),
    ]),
    dict(id='r2', kind='rank', dish='suki', pre=0.32, gap=0.22, post=0.55, lines=[
        L('metan', '第2位！すき焼き！', ('だいにい！', 'rank'), ('すきやき！', 'name')),
        L('zunda', '甘辛いお肉を、|とろ〜り卵にくぐらせて…|ごはん、おかわりなのだ！',
          ('あまからいお肉を、とろーり卵にくぐらせて、', 'pop1'), ('ごはん、おかわりなのだ！', 'pop2')),
    ]),
    dict(id='drum', kind='drum', pre=0.25, gap=0.20, post=1.55, lines=[
        L('metan', 'いよいよ、第1位の発表よ…！', ('いよいよ、だいいちいの発表よ！', None)),
        L('zunda', 'ドキドキするのだ…！', ('ドキドキするのだ！', None)),
    ]),
    dict(id='r1', kind='rank', dish='kimchi', pre=0.85, gap=0.22, post=0.60, lines=[
        L('metan', 'キムチ鍋〜！！', ('キムチなべー！', 'name')),
        L('zunda', 'ピリ辛で、|体の芯からポッカポカなのだ！', ('ピリ辛で、', 'pop1'), ('体の芯から、ポッカポカなのだ！', 'pop2')),
        L('metan', 'シメはラーメンに、|とろ〜りチーズよ！', ('シメはラーメンに、とろーりチーズよ！', 'shime')),
    ]),
    dict(id='outro', kind='outro', pre=0.45, gap=0.25, post=1.60, lines=[
        L('metan', 'あなたの推し鍋はどれ？|コメントで教えてね！', ('あなたの、おしなべはどれ？', 'ask'), ('コメントで教えてね！', 'comment')),
        L('zunda', 'フォローもよろしくなのだ！', ('フォローも、よろしくなのだ！', 'follow')),
    ]),
]
PART_GAP = 0.10  # 同じセリフ内のパーツ間の間


class Voice:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=ORT)
        self.synth = Synthesizer(ort, OpenJtalk(DICT))
        with VoiceModelFile.open(VVM) as m:
            self.synth.load_voice_model(m)

    def __call__(self, text, sp):
        cfg = SPEAKERS[sp]
        q = self.synth.create_audio_query(text, cfg['style'])
        q.speed_scale = cfg['speed']; q.pitch_scale = cfg['pitch']; q.intonation_scale = cfg['intonation']
        q.pre_phoneme_length = 0.04; q.post_phoneme_length = 0.06
        wav = self.synth.synthesis(q, cfg['style'])
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.006)[0]
        if len(idx):
            x = x[max(0, idx[0] - 240): idx[-1] + 960]
        f = min(240, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x


def main():
    voice = Voice()
    clips = []           # (開始秒, 波形)
    lines_out, scenes_out, sfx = [], [], []
    t = 0.0
    for sc in SCENES:
        start = t
        cur = start + sc['pre']
        ev = {}
        for li, ln in enumerate(sc['lines']):
            if li: cur += sc['gap']
            ls = cur
            for pi, p in enumerate(ln['parts']):
                if pi: cur += PART_GAP
                x = voice(p['say'], ln['speaker'])
                if p['key']: ev[p['key']] = round(cur - start, 3)
                clips.append((cur, x))
                cur += len(x) / SR
            ev[f'l{li + 1}'] = round(ls - start, 3)
            ev[f'l{li + 1}end'] = round(cur - start, 3)
            lines_out.append(dict(speaker=ln['speaker'], text=ln['text'], start=round(ls, 3), end=round(cur, 3), scene=sc['id']))
        dur = cur + sc['post'] - start
        dur = round(np.ceil(dur * FPS) / FPS, 4)  # フレーム境界に揃える
        s = dict(id=sc['id'], kind=sc['kind'], start=round(start, 4), dur=dur, ev=ev)
        if sc['kind'] == 'rank':
            d = DISHES[sc['dish']]
            s.update(dish=sc['dish'], **d)
            # 演出イベント(シーン内の相対秒)。映像と効果音の両方がこれを使う
            ev['stamp'] = round(ev.get('rank', ev['l1']) + 0.02, 3)
            ev['pot'] = round(ev['stamp'] + 0.22, 3)
            ev.setdefault('name', ev['l1'])
            ev['tag1'] = round(ev['l2'] + 0.15, 3)
            ev['tag2'] = round(ev.get('shime', ev['l2'] + 0.9), 3)
            ev['pop1t'] = round(ev.get('pop1', ev['l2']) + 0.1, 3)
            ev['pop2t'] = round(ev.get('pop2', ev['l2'] + 1.2) + 0.1, 3)
            if d['rank'] == 1:
                ev['stamp'] = 0.0; ev['pot'] = 0.0  # 1位はフタが飛んで登場
        scenes_out.append(s)
        t = start + dur

    total = round(t, 4)
    # 効果音イベント(絶対秒)
    for s in scenes_out:
        st, ev, k = s['start'], s['ev'], s['kind']
        if k == 'intro':
            sfx += [dict(t=st + 0.05, type='rattle', dur=2.4), dict(t=st + 0.55, type='stamp'), dict(t=st + ev['samui'], type='boing'),
                    dict(t=st + ev['title'], type='stamp'),
                    dict(t=st + ev['go'], type='sparkle')]
        elif k == 'rank':
            if s['rank'] != 1:
                sfx += [dict(t=st, type='whoosh'), dict(t=st + ev['stamp'], type='stamp'), dict(t=st + ev['pot'] + 0.25, type='plop')]
            else:
                sfx += [dict(t=st, type='crash'), dict(t=st, type='fanfare'), dict(t=st + 0.05, type='lidpop'),
                        dict(t=st + ev['l1end'], type='sparkle')]
            sfx += [dict(t=st + ev['name'] + 0.05, type='pop'),
                    dict(t=st + ev['tag1'], type='tick'), dict(t=st + ev['tag2'], type='tick'),
                    dict(t=st + ev['pop1t'], type='boing'), dict(t=st + ev['pop2t'], type='boing')]
        elif k == 'drum':
            sfx += [dict(t=st, type='whoosh'), dict(t=st + 0.25, type='drumroll', dur=s['dur'] - 0.25)]
        elif k == 'outro':
            sfx += [dict(t=st, type='whoosh')] + [dict(t=st + 0.25 + i * 0.14, type='tick') for i in range(5)]
            sfx += [dict(t=st + ev['ask'], type='pop'), dict(t=st + ev['follow'], type='sparkle')]

    # ---- 書き出し ----
    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for st, x in clips:
        i = int(st * SR); track[i:i + len(x)] += x[:len(track) - i]
    track = track[:int(total * SR)]
    track *= 0.89 / (np.max(np.abs(track)) or 1)
    with wave.open(os.path.join(BUILD, 'voice.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    tl = dict(fps=FPS, total=total, speakers={k: v['name'] for k, v in SPEAKERS.items()},
              scenes=scenes_out, lines=lines_out, sfx=sorted(sfx, key=lambda e: e['t']),
              ranking=sorted(({'id': k, **v} for k, v in DISHES.items()), key=lambda d: d['rank']))
    with open(os.path.join(BUILD, 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    with open(os.path.join(BUILD, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('window.TIMELINE = ' + json.dumps(tl, ensure_ascii=False) + ';\n')

    def ts(x):
        return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)) % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, ln in enumerate(lines_out, 1):
            f.write(f"{i}\n{ts(ln['start'])} --> {ts(min(ln['end'] + 0.25, total))}\n{SPEAKERS[ln['speaker']]['name']}：{ln['text'].replace('|', chr(10))}\n\n")

    for s in scenes_out:
        print(f"{s['start']:6.2f}s  {s['dur']:5.2f}s  {s['id']:6s} {s.get('name', '')}")
    print(f'total {total:.2f}s, {len(lines_out)} lines, {len(sfx)} sfx')


if __name__ == '__main__':
    main()
