# -*- coding: utf-8 -*-
"""assets/illust, assets/emoji の SVG を assets/svgs.js(window.SVGS)に埋め込む。file:// でも読めるようにするため。"""
import os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
d = {}
for sub in ('illust', 'emoji'):
    for f in sorted(glob.glob(os.path.join(HERE, 'assets', sub, '*.svg'))):
        d[sub + '/' + os.path.splitext(os.path.basename(f))[0]] = open(f, encoding='utf-8').read()
out = os.path.join(HERE, 'assets', 'svgs.js')
with open(out, 'w', encoding='utf-8') as fp:
    fp.write('window.SVGS = ' + json.dumps(d, ensure_ascii=False) + ';\n')
print('wrote', out, len(d), 'svgs', os.path.getsize(out) // 1024, 'KB')
