import sys, subprocess, numpy as np, json
SR=22050
p=sys.argv[1]
x=np.frombuffer(subprocess.run(['ffmpeg','-loglevel','error','-i',p,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout,np.float32)
hop=256; n=1024; fr=SR/hop
fr_=np.lib.stride_tricks.sliding_window_view(x,n)[::hop]*np.hanning(n)
S=np.abs(np.fft.rfft(fr_,axis=1))
flux=np.maximum(0,np.diff(np.log1p(S),axis=0)).sum(1)
flux=np.concatenate([[0],flux]); flux-=np.convolve(flux,np.ones(32)/32,'same'); flux=np.maximum(flux,0)
# fine tempo search
best=None
for bpm in np.arange(130,160,0.02):
    per=60/bpm*fr
    # phase search
    idx=np.arange(0,len(flux)-1,per)
    for ph in np.arange(0,per,per/48):
        v=flux[np.clip((idx+ph).astype(int),0,len(flux)-1)].sum()
        if best is None or v>best[0]: best=(v,bpm,ph/fr)
v,bpm,ph=best
print('bpm',round(bpm,3),'phase',round(ph,4))
# energy per 2s
rms=np.sqrt((fr_**2).mean(1)); t=np.arange(len(rms))/fr
for a in range(0,int(len(x)/SR),4):
    m=(t>=a)&(t<a+4); print(a, round(20*np.log10(rms[m].mean()+1e-9),1), end=' | ')
print()
# downbeat: which beat mod 4 has most low-frequency onset energy
lowS=np.abs(np.fft.rfft(fr_,axis=1))[:, :int(150/(SR/n))].sum(1)
lflux=np.maximum(0,np.diff(lowS,prepend=lowS[0]))
beat=60/bpm; bt=np.arange(ph,len(x)/SR,beat)
sc=[lflux[np.clip((bt[k::4]*fr).astype(int),0,len(lflux)-1)].sum() for k in range(4)]
print('downbeat scores',[round(s) for s in sc])
json.dump(dict(bpm=bpm,phase=ph,down=int(np.argmax(sc))),open(sys.argv[2],'w'))
