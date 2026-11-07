# -*- coding: utf-8 -*-
"""タイムライン(timeline.json)から演出イベントの時刻を算出する。映像(render.html)と音(audio.py)の両方がこの結果を使い、同期を保つ。"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

def build(tl):
    S = {s['id']: s for s in tl['scenes']}
    L = lambda sid, i: S[sid]['lines'][i]
    ev = []
    add = lambda kind, t, **kw: ev.append(dict(kind=kind, t=round(t, 3), **kw))
    q = S['quiz']
    # 心音: クイズの発話中、0.95 秒間隔
    t = 0.3
    while t < L('quiz', 1)['end']:
        add('heartbeat', t); t += 0.95
    # 選択肢の出現と、制限時間のカウントダウン
    add('choices', L('quiz', 1)['start'] + 0.2)
    timer0 = L('quiz', 1)['end'] + 0.15
    timer1 = q['end'] - 0.05
    add('timer', timer0, end=round(timer1, 3))
    for k in range(3):
        add('tick', timer0 + k * (timer1 - timer0) / 3, n=3 - k)
    # 正解表示
    a = S['answer']
    add('flash', a['start'])
    add('correct', a['start'] + 0.1)
    add('wrong', a['start'] + 0.5)
    add('stamp', L('answer', 1)['start'] + 0.55, label='最悪の選択')
    # 190万個のカウンター
    w = S['why']
    add('counter', L('why', 1)['start'] + 0.3, end=round(L('why', 1)['end'] + 0.1, 3))
    # FAST の4文字が叩き込まれる
    f = S['fast']
    add('riser', L('fast', 1)['start'] - 1.4, end=round(L('fast', 1)['start'], 3))
    for i in range(4):
        add('slam', L('fast', 1)['start'] + 0.05 + i * 0.14, i=i)
    add('flash', L('fast', 1)['start'] + 0.05 + 3 * 0.14)
    # 各文字の解説シーン: 開始にウーッシュ、異常が現れる瞬間に警告音
    for sid in ('F', 'A', 'S', 'T'):
        add('whoosh', S[sid]['start'])
    add('alert', L('F', 1)['start'] + 1.2)
    add('alert', L('A', 1)['start'] + 1.1)
    add('alert', L('S', 1)['start'] + 0.9)
    add('alarm', L('T', 1)['start'] + 0.9)
    add('pop', L('T', 2)['start'] + 0.1)
    # 4.5 時間のリング
    add('whoosh', S['tpa']['start'])
    add('ring', L('tpa', 0)['start'], end=round(S['tpa']['end'], 3))
    # NG 3 連スタンプ
    add('whoosh', S['ng']['start'])
    l = L('ng', 1)
    for k in range(3):
        add('stamp', l['start'] + 0.15 + k * (l['end'] - l['start']) / 3, label=['様子を見る', '自分で運転', '水を飲ませる'][k], i=k)
    # CTA
    add('riser', S['cta']['start'] - 1.2, end=round(S['cta']['start'], 3))
    add('ding', S['cta']['start'] + 0.05)
    add('pop', L('cta', 0)['start'] + 0.6)
    add('flash', S['cta']['start'])
    ev.sort(key=lambda e: e['t'])
    return ev

# BGM の強度(0..1)をシーンごとに決める
LEVELS = dict(quiz=0.3, answer=0.55, why=0.75, fast=0.85, F=1.0, A=1.0, S=1.0, T=1.0, tpa=0.8, ng=0.5, cta=1.0)

if __name__ == '__main__':
    tl = json.load(open(os.path.join(HERE, 'output', 'timeline.json')))
    for e in build(tl): print(e)
