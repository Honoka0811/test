# -*- coding: utf-8 -*-
"""イラスト素材を assets/ に集め、Canvas から読める assets/assets.js(data URL 埋め込み)を生成する。
- unDraw(https://undraw.co, unDraw License: 商用可・表記不要) … npm パッケージ undraw-svg から
- Fluent Emoji 3D(Microsoft, MIT License) … npm パッケージ @iconify-json/fluent-emoji から
使い方: python3 tools/build_assets.py [undraw-svg の svgs/ ディレクトリ] [fluent-emoji の icons.json]
"""
import sys, os, json, base64, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNDRAW = sys.argv[1] if len(sys.argv) > 1 else '/home/user/assets/npm/undraw-svg-2.0.0/svgs'
FLUENT = sys.argv[2] if len(sys.argv) > 2 else '/home/user/assets/npm/iconify-json-fluent-emoji-1.2.7/icons.json'
OUT = os.path.join(HERE, 'assets')
os.makedirs(OUT, exist_ok=True)

# シーンID → (unDraw イラスト名, アクセント色)。アクセント色は currentColor の部分に入る
UNDRAW_SCENES = {
    'intro': ('celebration', '#F5B700'),
    's1': ('doctor', '#1FA98A'),
    's2': ('running-wild', '#F2622E'),
    's4': ('eating-together', '#7B5CF5'),
    's5': ('savings', '#2E9E5B'),
    's6': ('education', '#2F7FE0'),
    's7': ('grandma', '#E8734A'),
    's8': ('coffee-with-friends', '#E0457B'),
    's9': ('traveling', '#F2A51A'),
    's10': ('clean-up', '#1E9BA8'),
    'outro': ('checklist', '#F5B700'),
}
EMOJI = """party-popper sparkles hundred-points star rocket glowing-star trophy thumbs-up folded-hands
stethoscope hospital check-mark-button flexed-biceps running-shoe woman-walking person-running
tooth toothbrush calendar bed zzz green-salad crescent-moon red-apple
money-bag chart-increasing-with-yen coin bank yen-banknote books graduation-cap laptop light-bulb
old-man old-woman house speech-balloon red-heart people-hugging handshake sparkling-heart two-hearts
airplane guitar camera mountain luggage package broom shield receipt check-box-with-check wastebasket
alarm-clock hourglass-not-done fire""".split()

def data_url(svg):
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode('utf-8')).decode('ascii')

out = {'undraw': {}, 'emoji': {}}
for sid, (name, color) in UNDRAW_SCENES.items():
    svg = open(os.path.join(UNDRAW, name + '.svg'), encoding='utf-8').read()
    svg = svg.replace('currentColor', color)
    m = re.search(r'viewBox="([\d. ]+)"', svg)
    vb = [float(v) for v in m.group(1).split()]
    if 'width=' not in svg[:400]:
        svg = svg.replace('<svg ', f'<svg width="{vb[2]:.0f}" height="{vb[3]:.0f}" ', 1)
    with open(os.path.join(OUT, f'undraw_{sid}_{name}.svg'), 'w', encoding='utf-8') as f:
        f.write(svg)
    out['undraw'][sid] = {'src': data_url(svg), 'w': vb[2], 'h': vb[3], 'name': name}

icons = json.load(open(FLUENT, encoding='utf-8'))['icons']
for name in EMOJI:
    body = icons[name]['body']
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           'width="512" height="512" viewBox="0 0 32 32">' + body + '</svg>')
    with open(os.path.join(OUT, f'emoji_{name}.svg'), 'w', encoding='utf-8') as f:
        f.write(svg)
    out['emoji'][name] = data_url(svg)

with open(os.path.join(OUT, 'assets.js'), 'w', encoding='utf-8') as f:
    f.write('// 自動生成: tools/build_assets.py\nwindow.ASSETS = ')
    json.dump(out, f, ensure_ascii=False)
    f.write(';\n')
print('wrote', os.path.join(OUT, 'assets.js'), f"{os.path.getsize(os.path.join(OUT, 'assets.js'))/1e6:.1f} MB",
      len(out['undraw']), 'undraw,', len(out['emoji']), 'emoji')
