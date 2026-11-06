# -*- coding: utf-8 -*-
"""output/timeline.json から YouTube 概要欄用の目次(チャプター)を出力する。"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
tl = json.load(open(os.path.join(HERE, 'output', 'timeline.json'), encoding='utf-8'))
sc = {s['id']: s for s in json.load(open(os.path.join(HERE, 'script.json'), encoding='utf-8'))['scenes']}
NUM = ['番外編', '其の一', '其の二', '其の三', '其の四', '其の五', '其の六', '其の七', '其の八']
for s in tl['scenes']:
    d = sc[s['id']]
    t = int(s['start'])
    label = {'hook': 'オープニング', 'history': 'そもそも大名家はどうなった？', 'outro': 'まとめ'}.get(s['id'])
    if not label:
        label = f"{NUM[d['no']]} {d['family']}" + ('(有馬記念)' if s['id'] == 'arima' else '')
    print(f'{t // 60}:{t % 60:02d} {label}')
