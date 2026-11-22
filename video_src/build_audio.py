import json,wave,numpy as np
L=json.load(open('lines_d.json'));AP=json.load(open('appear.json'))
SR=24000;t=0.35;prev=0;lines={};order=[];scene_start={0:0.0};cd=None
for i,l in enumerate(L):
    if l['s']!=prev: t+=0.45; scene_start[l['s']]=t-0.35; prev=l['s']
    lines[l['id']]={'start':round(t,3),'end':round(t+l['dur'],3),'sub':l['sub'],'s':l['s'],'i':i}
    t+=l['dur']+0.28
    if l.get('gap'): cd=t+0.1; t+=l['gap']
    if l.get('tail'): t+=l['tail']
total=t
ks=sorted(scene_start)
scenes=[{'start':round(scene_start[k],3),'end':round(scene_start[ks[j+1]] if j+1<len(ks) else total,3)} for j,k in enumerate(ks)]
appear={k:round(lines[a]['start']+(lines[a]['end']-lines[a]['start'])*f,3) for k,(a,f) in AP.items()}
TL={'lines':sorted(lines.values(),key=lambda x:x['i']),'byid':lines,'scenes':scenes,'total':round(total,3),'appear':appear,'cd':round(cd,3)}
json.dump(TL,open('timeline.json','w'),ensure_ascii=False)
def save(name,x,sr,ch=1):
    x=np.clip(x,-1,1);w=wave.open(name,'wb');w.setnchannels(ch);w.setsampwidth(2);w.setframerate(sr);w.writeframes((x*32767).astype(np.int16).tobytes());w.close()
voice=np.zeros(int(total*SR)+SR,dtype=np.float32)
for l in TL['lines']:
    w=wave.open(f"voice/{l['i']:02d}.wav");a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
    s=int(l['start']*SR);voice[s:s+len(a)]+=a
save('narration.wav',voice,SR)
# ---------- SFX ----------
BS=44100;n=int(total*BS)+BS;sfx=np.zeros(n);rng=np.random.default_rng(3)
def put(t0,x):
    s=int(t0*BS);e=min(n,s+len(x));sfx[s:e]+=x[:e-s]
def tone(f,d,dec,amp=.3,fend=None):
    x=np.arange(int(d*BS))/BS;fr=f if fend is None else f*(fend/f)**(x/d);ph=2*np.pi*np.cumsum(fr)/BS
    return amp*np.sin(ph)*np.exp(-x*dec)*np.minimum(1,x/0.003)
def whoosh(d=.35):
    m=int(d*BS);x=rng.standard_normal(m);env=np.sin(np.linspace(0,np.pi,m))**2
    y=np.zeros(m);a=0
    for i in range(m):  # moving one-pole lowpass
        c=0.05+0.5*(i/m);a+= c*(x[i]-a);y[i]=a
    return .22*y*env
pop=lambda:tone(900,.12,30,.22,fend=1500)
tick=lambda:tone(1400,.08,60,.2)
ding=lambda:tone(1320,.9,4,.18)+tone(1760,.9,5,.12)+np.pad(tone(2640,.6,7,.05),(0,int(.9*BS)-int(.6*BS)))
W=whoosh()
for j,s in enumerate(scenes[1:],1): put(s['start'],W)
for k,v in appear.items():
    if k=='ans': put(v,ding())
    elif k not in ('sw','end','badge'): put(v,pop())
put(lines['h1']['start']+0.02,tone(220,.5,6,.25,fend=110))  # hook thump
for k in range(3): put(cd+k,tick())
save('sfx.wav',np.stack([sfx,sfx],1).reshape(-1),BS,2)
# ---------- BGM (light, bouncy, 100bpm) ----------
bpm=100;beat=60/bpm;bar=4*beat;Lb=np.zeros(n);Rb=np.zeros(n)
def note(m):return 440*2**((m-69)/12)
def add(buf,st,d,f,amp,att=.01,rel=.4,harm=(1,.3,.1)):
    s=int(st*BS);e=min(n,int((st+d+rel)*BS))
    if s>=n:return
    x=np.arange(e-s)/BS;env=np.minimum(1,x/att)*np.where(x<d,1,np.exp(-(x-d)/(rel/4)))*np.exp(-x*1.2)
    buf[s:e]+=amp*env*sum(h*np.sin(2*np.pi*f*(k+1)*x) for k,h in enumerate(harm))
prog=[[60,64,67,71],[57,60,64,67],[53,57,60,64],[55,59,62,65]] # Cmaj7 Am7 Fmaj7 G7
bass=[36,33,29,31];mel=[76,74,72,74,76,79,76,74, 72,71,69,71,72,76,74,72]
tb=0;b=0
while tb<total:
    ch=prog[b%4]
    for v,m in enumerate(ch): add(Lb if v%2 else Rb,tb,bar*.9,note(m),.035,att=.3,rel=1,harm=(1,.15))
    for k in range(4):
        add(Lb,tb+k*beat,beat*.5,note(bass[b%4]+(7 if k==2 else 0)),.11,harm=(1,.6,.2));add(Rb,tb+k*beat,beat*.5,note(bass[b%4]+(7 if k==2 else 0)),.11,harm=(1,.6,.2))
        for h in (0,1):  # off-beat chord stabs (ukulele-ish)
            if h==1:
                for m in ch[1:]: add(Lb,tb+k*beat+beat/2,.06,note(m+12),.025,att=.002,rel=.25,harm=(1,.5,.25)); add(Rb,tb+k*beat+beat/2,.06,note(m+12),.025,att=.002,rel=.25,harm=(1,.5,.25))
        if b>=1:
            s=int((tb+k*beat)*BS);m=min(n,s+int(.2*BS));x=np.arange(m-s)/BS
            kk=.2*np.sin(2*np.pi*(50+80*np.exp(-x*35))*x)*np.exp(-x*16);Lb[s:m]+=kk;Rb[s:m]+=kk
    if b%8>=4:  # glockenspiel melody every other phrase
        for k in range(8): add(Lb if k%2 else Rb,tb+k*beat/2,.05,note(mel[(b%2)*8+k]),.03,att=.002,rel=.6,harm=(1,.1,.05))
    b+=1;tb+=bar
fade=np.ones(n);fi=int(.6*BS);fo=int(4*BS);fade[:fi]=np.linspace(0,1,fi);fade[-fo:]=np.linspace(1,0,fo)
st=np.stack([Lb*fade,Rb*fade],1);st/=np.abs(st).max()*1.1
save('bgm.wav',st.reshape(-1),BS,2)
print('total',round(total,1),'cd',round(cd,1));print([(i,s['start']) for i,s in enumerate(scenes)])
