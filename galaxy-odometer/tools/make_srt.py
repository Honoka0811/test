# -*- coding: utf-8 -*-
"""build/timeline.json → 字幕ファイル(SRT)。YouTube Studio の「字幕」にアップロードする用。"""
import json, os, sys

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
tl = json.load(open(os.path.join(HERE, 'build', 'timeline.json'), encoding='utf-8'))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build', 'subtitles_ja.srt')


def ts(t):
    ms = int(round(t * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


with open(out, 'w', encoding='utf-8') as f:
    for i, line in enumerate(tl['lines'], 1):
        nxt = tl['lines'][i]['start'] if i < len(tl['lines']) else tl['duration']
        end = min(line['end'] + 0.25, nxt - 0.02, tl['duration'])
        f.write(f"{i}\n{ts(line['start'])} --> {ts(end)}\n{''.join(c['show'] for c in line['chunks'])}\n\n")
print('wrote', out)
