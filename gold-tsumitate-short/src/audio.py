import json,wave,numpy as np,sys
W=sys.argv[1]; SR=44100
lines=json.load(open(f"{W}/voice/lines.json"))
def readwav(p):
    with wave.open(p) as w: sr=w.getframerate(); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
    t=np.arange(int(len(x)*SR/sr))*sr/SR; return np.interp(t,np.arange(len(x)),x)
# timeline
t=0.35; tl=[]
for k,txt,d in lines:
    if k=="s8": t+=1.1
    tl.append(dict(k=k,text=txt,start=round(t,3),dur=d)); t+=d+0.22
END=t+2.2
json.dump(dict(lines=tl,end=END),open(f"{W}/timeline.json","w"),ensure_ascii=False,indent=1)
S={d['k']:d for d in tl}
N=int(END*SR); voice=np.zeros(N); 
for d in tl:
    v=readwav(f"{W}/voice/{d['k']}.wav"); i=int(d['start']*SR); voice[i:i+len(v)]+=v[:N-i]
rng=np.random.default_rng(7)
def env(n,a,dcy): x=np.arange(n)/SR; return np.minimum(x/a,1)*np.exp(-x/dcy)
def add(buf,sig,t0,g=1):
    i=int(t0*SR); 
    if i>=len(buf): return
    s=sig[:len(buf)-i]; buf[i:i+len(s)]+=g*s
def lp(x,fc):
    a=np.exp(-2*np.pi*fc/SR); y=np.zeros_like(x); acc=0
    from scipy.signal import lfilter
    return lfilter([1-a],[1,-a],x)
try: import scipy
except: pass
from scipy.signal import butter,sosfilt
def bp(x,lo,hi): return sosfilt(butter(2,[lo,hi],'band',fs=SR,output='sos'),x)
def hp(x,f): return sosfilt(butter(2,f,'high',fs=SR,output='sos'),x)
def kick():
    n=int(.5*SR); x=np.arange(n)/SR; f=45+90*np.exp(-x/.04); ph=2*np.pi*np.cumsum(f)/SR
    return np.tanh(2*np.sin(ph)*np.exp(-x/.18))
def clap():
    n=int(.25*SR); return bp(rng.standard_normal(n),900,5000)*env(n,.002,.06)*1.6
def hat(o=False):
    n=int((.18 if o else .05)*SR); return hp(rng.standard_normal(n),7000)*env(n,.001,.05 if o else .012)
def b808(f,dur):
    n=int(dur*SR); x=np.arange(n)/SR; ff=f*(1+0.5*np.exp(-x/.03)); ph=2*np.pi*np.cumsum(ff)/SR
    return np.tanh(1.8*np.sin(ph))*np.minimum(x/.005,1)*np.exp(-x/(dur*.7))
def pluck(f,dur=.35):
    n=int(dur*SR); x=np.arange(n)/SR
    s=np.sin(2*np.pi*f*x)+.4*np.sin(2*np.pi*2*f*x)*np.exp(-x/.05)+.2*np.sin(2*np.pi*3.01*f*x)*np.exp(-x/.03)
    return s*env(n,.003,.12)
def pad(fs,dur):
    n=int(dur*SR); x=np.arange(n)/SR; s=np.zeros(n)
    for f in fs:
        for dt in(-.6,0,.6): s+=((x*(f+dt))%1*2-1)
    s=lp(s/len(fs)/3,1200); a=np.minimum(x/.3,1)*np.minimum((dur-x)/.3,1); return s*a
m2f=lambda m:440*2**((m-69)/12)
BPM=140; B=60/BPM; BAR=4*B
chords=[(48,[60,63,67]),(44,[60,63,68]),(51,[58,63,67]),(46,[58,62,65])] # Cm Ab Eb Bb
drums=np.zeros(N); bass=np.zeros(N); mel=np.zeros(N); padb=np.zeros(N); fx=np.zeros(N)
s7=S['s7']['start']; s8=S['s8']['start']; brk0=s7-0.1
def sec(t):
    if t>=brk0 and t<s8: return 'break'
    if t>=s8: return 'drop'
    return 'main'
nb=int(END/BAR)+1
for b in range(nb):
    t0=b*BAR; root,ch=chords[b%4]; sc=sec(t0)
    # pad
    if sc!='break' or True:
        add(padb,pad([m2f(m) for m in ch],BAR),t0,.5 if sc!='break' else .35)
    for st in range(16):
        tt=t0+st*B/4; s=sec(tt)
        if s=='break': continue
        if st in(0,10): add(drums,kick(),tt,.9)
        if st==8: add(drums,clap(),tt,.55)
        if st%2==0: add(drums,hat(),tt,.18 if st%4 else .25)
        if s=='drop' and st in(13,15): add(drums,hat(),tt,.15)
        if st==14 and b%2==1: add(drums,hat(True),tt,.12)
        if st in(0,10): add(bass,b808(m2f(root-12+12),B*(2.5 if st==0 else 1.5)),tt,.55)
        arp=[ch[0],ch[1],ch[2],ch[1]+12,ch[2],ch[1]+12,ch[0]+12,ch[2]]
        if st%2==0 or s=='drop':
            n_=arp[st%8]+12; add(mel,pluck(m2f(n_)),tt,.16 if s=='main' else .2)
# break: riser + snare roll accelerating
L=s8-brk0
n=int((L-.25)*SR); x=np.arange(n)/SR; riser=hp(rng.standard_normal(n),800)*(x/(L-.25))**2*.35
sweep=np.sin(2*np.pi*np.cumsum(200+1500*(x/(L))**2)/SR)*(x/L)**2*.12
add(fx,riser+sweep,brk0)
tt=brk0; step=.18
while tt<s8-.3:
    add(fx,clap(),tt,.15+.35*(tt-brk0)/L); tt+=step; step=max(.045,step*.82)
# impact at s8
n=int(2.5*SR); x=np.arange(n)/SR
boom=np.tanh(3*np.sin(2*np.pi*np.cumsum(35+80*np.exp(-x/.08))/SR))*np.exp(-x/.7)
crash=hp(rng.standard_normal(n),3000)*np.exp(-x/.8)*.25
add(fx,boom*.9+crash,s8)
# sfx: whoosh at each scene start, chings
def whoosh():
    n=int(.4*SR); x=np.arange(n)/SR; w=rng.standard_normal(n)
    out=np.zeros(n)
    for i in range(0,n,512):
        f=600+5000*np.sin(np.pi*i/n); seg=w[i:i+512]
    out=bp(w,800,6000)*np.sin(np.pi*x/.4)**2; return out*.3
def ching():
    n=int(.6*SR); x=np.arange(n)/SR
    return sum(a*np.sin(2*np.pi*f*x)*np.exp(-x/d) for f,a,d in[(2093,.5,.25),(3136,.35,.18),(5274,.25,.1),(4186,.2,.15)])*.35
for d in tl:
    if d['k'] not in('s1','s8'): add(fx,whoosh(),d['start']-.2)
for k,cnt in(('s2',6),('s5',8)):
    for i in range(cnt): add(fx,ching(),S[k]['start']+.3+i*S[k]['dur']*.8/cnt,.5)
for i in range(14): add(fx,ching(),s8+.05+i*.12,.35)
add(fx,ching(),S['s4']['start']+S['s4']['dur']*.55,.9)
# mix with ducking
venv=np.convolve(np.abs(voice),np.ones(2205)/2205,'same'); venv=np.convolve((venv>0.01).astype(float),np.ones(8820)/8820,'same')
music=drums*.8+bass*.75+mel+padb*.35
music*=1-.45*np.clip(venv,0,1)
fade=np.ones(N); fn=int(2.0*SR); fade[-fn:]=np.linspace(1,0,fn); music*=fade
intro=np.minimum(np.arange(N)/(0.05*SR),1); music*=intro
mix=music*.45+voice*1.0+fx*.55
mix/=np.max(np.abs(mix))*1.05
st=np.stack([mix,mix],1)
with wave.open(f"{W}/mix.wav","wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype(np.int16).tobytes())
print("END",END); [print(d['k'],d['start'],d['dur']) for d in tl]
