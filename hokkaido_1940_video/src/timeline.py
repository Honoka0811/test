import json, math, sys
sys.path.insert(0, sys.argv[1] if len(sys.argv)>1 else '.')
from lines import LINES
durs = json.load(open('durs.json'))
CITIES = {
 'r10': dict(rank=10, name='帯広市', kind='市', pop=36555,  lat=42.9236, lon=143.1966),
 'r9':  dict(rank=9,  name='三笠山村', kind='村', pop=38579, lat=43.2457, lon=141.8757),
 'r8':  dict(rank=8,  name='美唄町', kind='町', pop=54122,  lat=43.3331, lon=141.8536),
 'r7':  dict(rank=7,  name='釧路市', kind='市', pop=63180,  lat=42.9849, lon=144.3820),
 'r6':  dict(rank=6,  name='夕張町', kind='町', pop=64998,  lat=43.0567, lon=141.9739),
 'r5':  dict(rank=5,  name='旭川市', kind='市', pop=87514,  lat=43.7706, lon=142.3650),
 'r4':  dict(rank=4,  name='室蘭市', kind='市', pop=107628, lat=42.3152, lon=140.9738),
 'r3':  dict(rank=3,  name='小樽市', kind='市', pop=164282, lat=43.1907, lon=140.9947),
 'r2':  dict(rank=2,  name='函館市', kind='市', pop=203862, lat=41.7687, lon=140.7288),
 'r1':  dict(rank=1,  name='札幌市', kind='市', pop=206103, lat=43.0621, lon=141.3544),
}
NOTE = {'r9':'現・三笠市', 'r8':'現・美唄市', 'r6':'現・夕張市'}
subs = {k:s for k,_,s in LINES}
segs = []
t = 0.0
# intro
segs.append(dict(key='intro', start=0.0, reveal=0.0, voice=0.8, end=math.ceil(0.8+durs['intro']+0.4)))
t = segs[-1]['end']
for k in ['r10','r9','r8','r7','r6','r5','r4','r3','r2','r1a','r1']:
    R = t + 1.0
    v = R + (0.1 if k=='r1a' else 0.15)
    if k == 'r1a':
        L = 3.0
    else:
        L = math.ceil(0.15 + durs[k] + 0.45)
    segs.append(dict(key=k, start=t, reveal=R, voice=v, end=R+L))
    t = R + L
R = t + 1.0
segs.append(dict(key='outro', start=t, reveal=R, voice=R+0.3, end=R+math.ceil(durs['outro']+2.2)))
for s in segs:
    s['sub'] = subs[s['key']]; s['dur'] = durs[s['key']]
    if s['key'] in CITIES: s.update(CITIES[s['key']]); s['note']=NOTE.get(s['key'],'')
json.dump(dict(segs=segs, total=segs[-1]['end'], bpm=120), open('timeline.json','w'), ensure_ascii=False, indent=1)
for s in segs: print(s['key'], s['start'], s['reveal'], round(s['voice'],2), s['end'])
print('total', segs[-1]['end'])
