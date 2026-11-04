import json,math,sys,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from multiprocessing import Pool
W_=sys.argv[1]; FPS=30; WD,HT=1080,1920
TL=json.load(open(f"{W_}/timeline.json")); END=TL['end']; S={d['k']:d for d in TL['lines']}
FD=f"{W_}/fonts/package"
F={w:f"{FD}/{w}/NotoSansJP_{w}.ttf" for w in["900Black","700Bold","500Medium"]}
_fc={}
def font(sz,w="900Black"):
    k=(sz,w)
    if k not in _fc: _fc[k]=ImageFont.truetype(F[w],sz)
    return _fc[k]
GOLD=(255,206,64); GOLD2=(255,170,0); WHITE=(255,255,255); RED=(255,70,70); DARK=(20,14,4)
_tc={}
def timg(text,sz,fill=WHITE,stroke=10,sc=(0,0,0),w="900Black",grad=False):
    k=(text,sz,fill,stroke,sc,w,grad)
    if k in _tc: return _tc[k]
    f=font(sz,w); bb=f.getbbox(text,stroke_width=stroke); tw,th=bb[2]-bb[0]+20,bb[3]-bb[1]+20
    im=Image.new("RGBA",(tw,th),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.text((10-bb[0],10-bb[1]),text,font=f,fill=fill,stroke_width=stroke,stroke_fill=sc)
    if grad:
        m=Image.new("L",(tw,th),0); ImageDraw.Draw(m).text((10-bb[0],10-bb[1]),text,font=f,fill=255)
        g=np.zeros((th,tw,4),np.uint8); y=np.linspace(0,1,th)[:,None]
        top=np.array([255,240,170]); bot=np.array([230,150,0])
        col=(top*(1-y)+bot*y)[:, :]; g[...,:3]=np.repeat(col[:,None,:],tw,1).reshape(th,tw,3) if col.ndim==2 else col
        g[...,3]=np.array(m); im.alpha_composite(Image.fromarray(g))
    _tc[k]=im; return im
def put(fr,im,cx,cy,scale=1.0,alpha=1.0,rot=0):
    if scale<=0.01 or alpha<=0.01: return
    if scale!=1: im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.BILINEAR)
    if rot: im=im.rotate(rot,expand=True,resample=Image.BILINEAR)
    if alpha<1:
        im=im.copy(); a=im.getchannel("A").point(lambda v:int(v*alpha)); im.putalpha(a)
    fr.alpha_composite(im,(int(cx-im.width/2),int(cy-im.height/2)))
def txt(fr,s,sz,cx,cy,**kw):
    sc=kw.pop('scale',1); al=kw.pop('alpha',1); rot=kw.pop('rot',0)
    put(fr,timg(s,sz,**kw),cx,cy,sc,al,rot)
clamp=lambda x:max(0.,min(1.,x))
def ease(x): x=clamp(x); return 1-(1-x)**3
def back(x):
    x=clamp(x); c1=1.9; c3=c1+1; return 1+c3*(x-1)**3+c1*(x-1)**2
def pop(lt,t0,d=.35): return back((lt-t0)/d) if lt>=t0 else 0
# background
yy,xx=np.mgrid[0:HT,0:WD]; r=np.sqrt(((xx-WD/2)/WD)**2+((yy-HT*.45)/HT)**2)
bg=np.zeros((HT,WD,3)); c0=np.array([48,34,8]); c1=np.array([6,6,14])
k=np.clip(r/0.75,0,1)[...,None]; bg=c0*(1-k)+c1*k
BG=Image.fromarray(bg.astype(np.uint8)).convert("RGBA")
rg=np.random.default_rng(3); PN=55; P=dict(x=rg.uniform(0,WD,PN),sp=rg.uniform(40,140,PN),ph=rg.uniform(0,HT,PN),s=rg.uniform(2,7,PN),tw=rg.uniform(0,6.28,PN))
def particles(fr,t,boost=0):
    d=ImageDraw.Draw(fr)
    for i in range(PN):
        y=(P['ph'][i]-t*P['sp'][i]*(1+boost))%HT; x=P['x'][i]+20*math.sin(t*.8+P['tw'][i])
        a=int(120+100*math.sin(t*3+P['tw'][i])); s=P['s'][i]
        d.ellipse((x-s,y-s,x+s,y+s),fill=(255,210,90,max(0,a)))
CAP={"s1":"毎月たった5,000円\n30年 金を積み立てたら\n今いくら？","s2":"1996年から毎月5,000円\n払ったお金は合計180万円","s3":"当時の金は\n1gたったの1,400円","s4":"それが今や約22,000円！\n15倍以上に爆上がり！","s5":"積み上がった金は\n約675グラム","s6":"その半分以上は\n金が安かった最初の10年で\n買えていた","s7":"気になる評価額は…","s8":"なんと約1,480万円！\n元本の約8倍！","s9":"安い時にたくさん買える\nこれが積立の力","s10":"あなたなら何を積み立てる？\nコメントで教えて！"}
def caption(fr,t):
    for d in TL['lines']:
        if d['start']-.05<=t<d['start']+d['dur']+.15:
            ls=CAP[d['k']].split("\n"); y0=1560-(len(ls)-1)*42
            p=ease((t-d['start']+.05)/.15)
            # box
            ov=Image.new("RGBA",(WD,HT),(0,0,0,0)); od=ImageDraw.Draw(ov)
            od.rounded_rectangle((60,y0-60,WD-60,y0+len(ls)*84-24),28,fill=(0,0,0,int(150*p)))
            fr.alpha_composite(ov)
            for i,l in enumerate(ls): txt(fr,l,62,WD/2,y0+i*84,stroke=7,alpha=p,scale=.9+.1*p)
def header(fr,t):
    txt(fr,"金を30年 積み立てたら…",84,WD/2,175,grad=True,stroke=10,sc=(40,20,0))
    ov=Image.new("RGBA",(WD,HT),(0,0,0,0)); od=ImageDraw.Draw(ov)
    od.rounded_rectangle((250,250,830,330),40,fill=(255,206,64,235)); fr.alpha_composite(ov)
    txt(fr,"毎月5,000円 × 360回",44,WD/2,288,fill=DARK,stroke=0)
def footer(fr,t):
    txt(fr,"VOICEVOX:青山龍星",30,WD-200,1870,fill=(220,220,220),stroke=3,w="500Medium")
    if t>S['s8']['start']-.2:
        txt(fr,"※手数料・税金を除く概算。価格は田中貴金属の年平均等から推計",26,WD/2,1795,fill=(210,210,210),stroke=3,w="500Medium")
def fmt(n): return f"{int(n):,}"
PR=[(1996,1400),(1997,1330),(1998,1290),(1999,1060),(2000,1014),(2001,1026),(2002,1290),(2003,1388),(2004,1440),(2005,1619),(2006,2355),(2007,2570),(2008,2937),(2009,2980),(2010,3477),(2011,4000),(2012,4450),(2013,4560),(2014,4400),(2015,4564),(2016,4400),(2017,4600),(2018,4620),(2019,5100),(2020,6122),(2021,6402),(2022,7649),(2023,8834),(2024,11718),(2025,17302),(2026,21927)]
def stamp(fr,s,cx,cy,lt,t0,col=RED,sz=96,rot=-12):
    if lt<t0: return
    p=clamp((lt-t0)/.18); sc=2.2-1.2*ease(p)
    im=timg(s,sz,fill=WHITE,stroke=0)
    pad=Image.new("RGBA",(im.width+50,im.height+30),(0,0,0,0)); d=ImageDraw.Draw(pad)
    d.rounded_rectangle((0,0,pad.width-1,pad.height-1),24,fill=col+(255,),outline=WHITE,width=6); pad.alpha_composite(im,(25,15))
    put(fr,pad,cx,cy,sc,p,rot)
def scene(fr,t):
    def L(k): return t-S[k]['start']
    if t<S['s2']['start']-.2:
        lt=L('s1')+.35
        p=max(pop(lt,0),0); 
        txt(fr,"毎月",70,WD/2,520,fill=WHITE,stroke=8,scale=p)
        z=1+.03*math.sin(lt*6)
        txt(fr,"5,000円",210,WD/2,700,grad=True,stroke=14,sc=(60,30,0),scale=pop(lt,.15)*z)
        txt(fr,"× 30年",130,WD/2,920,fill=WHITE,stroke=12,scale=pop(lt,1.9))
        if lt>3.4:
            sh=8*math.sin(lt*60)*max(0,1-(lt-3.4)/.4)
            txt(fr,"今 いくら？",150,WD/2+sh,1170,fill=GOLD,stroke=14,scale=pop(lt,3.4))
            txt(fr,"?",240,930,1030,fill=RED,stroke=12,scale=pop(lt,3.7),rot=15*math.sin(lt*4))
    elif t<S['s3']['start']-.2:
        lt=L('s2')+.2; dur=S['s2']['dur']; p=ease((lt-.4)/(dur-.6))
        a=ease(lt/.3)
        d=ImageDraw.Draw(fr); x0,x1,y=140,940,620
        d.rounded_rectangle((x0,y-22,x1,y+22),22,fill=(60,60,70,255))
        d.rounded_rectangle((x0,y-22,x0+max(44,(x1-x0)*p),y+22),22,fill=GOLD2+(255,))
        txt(fr,"1996",56,x0+40,y-80,alpha=a,stroke=6); txt(fr,"2026",56,x1-40,y-80,alpha=a,stroke=6)
        yr=1996+int(30*p); txt(fr,f"{yr}年",64,x0+(x1-x0)*p,y+80,fill=GOLD,stroke=7,alpha=a)
        # coins stacking
        nc=int(p*10)
        for i in range(nc):
            cy=1340-i*24; d.ellipse((440,cy-26,640,cy+26),fill=(200,140,0,255),outline=(255,230,120,255),width=4)
        txt(fr,"払ったお金の合計",54,WD/2,800,stroke=6,alpha=a)
        txt(fr,fmt(1800000*p)+"円",130,WD/2,930,grad=True,stroke=12,sc=(60,30,0),alpha=a)
    elif t<S['s4']['start']-.2:
        lt=L('s3')+.2; d=ImageDraw.Draw(fr); p=pop(lt,0,.4)
        card=Image.new("RGBA",(720,560),(0,0,0,0)); cd=ImageDraw.Draw(card)
        cd.rounded_rectangle((0,0,719,559),40,fill=(255,250,235,255),outline=GOLD2,width=10)
        im=timg("1996年",70,fill=DARK,stroke=0); card.alpha_composite(im,(360-im.width//2,40))
        im=timg("金 1g",90,fill=(150,100,0),stroke=0); card.alpha_composite(im,(360-im.width//2,150))
        im=timg("1,400円",150,fill=(200,30,30),stroke=0); card.alpha_composite(im,(360-im.width//2,290))
        put(fr,card,WD/2,850,p,1,-3+3*p)
        stamp(fr,"安っ！",820,560,lt,1.3)
    elif t<S['s5']['start']-.2:
        lt=L('s4')+.2; dur=S['s4']['dur']; p=ease(lt/(dur*.6))
        d=ImageDraw.Draw(fr); X0,X1,Y0,Y1=150,950,1300,520
        for v in(5000,10000,15000,20000):
            yv=Y0-(Y0-Y1)*v/22000; d.line((X0,yv,X1,yv),fill=(255,255,255,40),width=2)
            txt(fr,f"{v//1000}千" if v<10000 else f"{v//10000}万" if v%10000==0 else "1.5万",30,X0-55,yv,stroke=3,w="500Medium")
        d.line((X0,Y0,X1,Y0),fill=(255,255,255,140),width=4)
        txt(fr,"1996",36,X0,Y0+40,stroke=4); txt(fr,"2026",36,X1,Y0+40,stroke=4)
        pts=[(X0+(X1-X0)*(y-1996)/30,Y0-(Y0-Y1)*v/22000) for y,v in PR]
        n=p*(len(pts)-1); i=int(n); f=n-i; sel=pts[:i+1]
        if i<len(pts)-1: sel=sel+[(pts[i][0]+(pts[i+1][0]-pts[i][0])*f,pts[i][1]+(pts[i+1][1]-pts[i][1])*f)]
        poly=sel+[(sel[-1][0],Y0),(X0,Y0)]
        ov=Image.new("RGBA",(WD,HT),(0,0,0,0)); ImageDraw.Draw(ov).polygon(poly,fill=(255,190,40,70)); fr.alpha_composite(ov)
        d.line(sel,fill=GOLD+(255,),width=12,joint="curve")
        ex,ey=sel[-1]; d.ellipse((ex-16,ey-16,ex+16,ey+16),fill=WHITE)
        cur=int(np.interp(1996+30*p,[y for y,_ in PR],[v for _,v in PR]))
        txt(fr,f"1g {fmt(cur)}円",80,WD/2,440,grad=True,stroke=10,sc=(60,30,0))
        stamp(fr,"15倍↑",760,800,lt,dur*.55,sz=110)
    elif t<S['s6']['start']-.2:
        lt=L('s5')+.2; dur=S['s5']['dur']; p=ease(lt/(dur*.75)); d=ImageDraw.Draw(fr)
        rows=[6,5,4,3,2,1]; tot=sum(rows); nb=int(p*tot+.001); c=0
        for ri,nr in enumerate(rows):
            for j in range(nr):
                if c>=nb: break
                bw=150; x=WD/2-nr*bw/2+j*bw+bw/2; y=1290-ri*80
                d.polygon([(x-68,y+34),(x+68,y+34),(x+50,y-34),(x-50,y-34)],fill=(230,170,20,255),outline=(255,240,160,255))
                d.polygon([(x-40,y-28),(x+40,y-28),(x+30,y-10),(x-30,y-10)],fill=(255,225,110,255)); c+=1
        txt(fr,f"{675*p:.0f}g",200,WD/2,620,grad=True,stroke=14,sc=(60,30,0),scale=1+.06*(p==1)*math.sin(lt*10))
    elif t<S['s7']['start']-.2:
        lt=L('s6')+.2; dur=S['s6']['dur']; p=ease((lt-.2)/1.2); d=ImageDraw.Draw(fr)
        X0,X1,Y=110,970,860; w1=(X1-X0)*441/675*p
        d.rounded_rectangle((X0,Y-90,X1,Y+90),30,fill=(70,70,80,255))
        d.rounded_rectangle((X0,Y-90,X0+max(60,w1),Y+90),30,fill=GOLD2+(255,))
        txt(fr,"最初の10年",56,X0+(X1-X0)*441/675/2,Y-160,fill=GOLD,stroke=6,alpha=p)
        txt(fr,"441g",96,X0+(X1-X0)*441/675/2,Y,fill=WHITE,stroke=8,alpha=p)
        txt(fr,"残り20年",44,X0+(X1-X0)*(441+117)/675,Y-160,stroke=5,alpha=p)
        txt(fr,"234g",60,X0+(X1-X0)*(441+117)/675,Y,stroke=6,alpha=p)
        txt(fr,"全体の 65%！",110,WD/2,1150,grad=True,stroke=12,sc=(60,30,0),scale=pop(lt,1.8))
        txt(fr,"価格が安い＝たくさん買える",48,WD/2,560,stroke=6,alpha=ease((lt-2.6)/.3))
    elif t<S['s8']['start']:
        lt=L('s7')+.2; tot=S['s8']['start']-S['s7']['start']+.2
        ov=Image.new("RGBA",(WD,HT),(0,0,0,int(160*ease(lt/.5)))); fr.alpha_composite(ov)
        sh=(lt/tot)**3*14; dx=sh*math.sin(lt*70); dy=sh*math.cos(lt*53)
        txt(fr,"評価額は…",150,WD/2+dx,860+dy,grad=True,stroke=12,sc=(60,30,0),scale=.8+.35*lt/tot)
        txt(fr,"？？？？？円",110,WD/2+dx,1100+dy,fill=WHITE,stroke=10,alpha=ease((lt-1)/.4))
    elif t<S['s9']['start']-.2:
        lt=L('s8'); p=ease(lt/1.3)
        v=14800000*p
        sh=max(0,1-lt/.5)*24
        txt(fr,"現在の評価額",64,WD/2,560,stroke=7)
        txt(fr,fmt(v),168,WD/2+sh*math.sin(lt*80),800,grad=True,stroke=14,sc=(60,30,0),scale=1+.08*max(0,1-abs(lt-1.35)/.25))
        txt(fr,"円",110,WD/2,980,fill=GOLD,stroke=10)
        stamp(fr,"元本の約8.2倍",WD/2,1210,lt,2.0,col=(220,30,30),sz=88,rot=-6)
        # burst
        if lt<2.5:
            d=ImageDraw.Draw(fr); rg2=np.random.default_rng(11)
            for i in range(70):
                ang=rg2.uniform(0,6.28); sp=rg2.uniform(500,1500); s=rg2.uniform(5,14)
                x=WD/2+math.cos(ang)*sp*lt; y=800+math.sin(ang)*sp*lt+600*lt*lt
                a=int(255*max(0,1-lt/2.5)); d.ellipse((x-s,y-s,x+s,y+s),fill=(255,215,80,a))
        if lt<.25:
            fr.alpha_composite(Image.new("RGBA",(WD,HT),(255,255,240,int(255*(1-lt/.25)))))
    elif t<S['s10']['start']-.2:
        lt=L('s9')+.2; p=ease((lt-.1)/1.0); d=ImageDraw.Draw(fr); B=1300
        h1=760*180/1480; h2=760*p
        d.rounded_rectangle((200,B-h1,440,B),20,fill=(150,150,160,255))
        d.rounded_rectangle((640,B-max(30,h2),880,B),20,fill=GOLD2+(255,))
        txt(fr,"払ったお金",44,320,B+50,stroke=5); txt(fr,"180万円",60,320,B-h1-50,stroke=6)
        txt(fr,"今の価値",44,760,B+50,stroke=5,fill=GOLD); txt(fr,f"{int(1480*p)}万円",72,760,B-max(30,h2)-55,grad=True,stroke=8,sc=(60,30,0))
    else:
        lt=L('s10')+.2
        txt(fr,"あなたなら",90,WD/2,560,stroke=9,scale=pop(lt,0))
        txt(fr,"何を積み立てる？",116,WD/2,720,grad=True,stroke=12,sc=(60,30,0),scale=pop(lt,.25))
        pb=1+.07*math.sin(lt*7)
        ov=Image.new("RGBA",(620,150),(0,0,0,0)); od=ImageDraw.Draw(ov); od.rounded_rectangle((0,0,619,149),75,fill=(230,40,40,255))
        im=timg("コメントで教えて！",56,stroke=0); ov.alpha_composite(im,(310-im.width//2,75-im.height//2))
        put(fr,ov,WD/2,1000,pop(lt,1.6)*pb)
        txt(fr,"フォローで次の検証もチェック",50,WD/2,1200,fill=GOLD,stroke=6,alpha=ease((lt-2.6)/.4))
def frame(i):
    t=i/FPS; fr=BG.copy()
    boost=2.5 if S['s8']['start']<=t<S['s8']['start']+2 else 0
    particles(fr,t,boost); header(fr,t); scene(fr,t); caption(fr,t); footer(fr,t)
    return fr.convert("RGB").tobytes()
if __name__=="__main__":
    import subprocess
    n=int(END*FPS)
    if len(sys.argv)>2:
        for s in sys.argv[2].split(","):
            i=int(float(s)*FPS); Image.frombytes("RGB",(WD,HT),frame(i)).save(f"{W_}/prev_{s}.png")
        sys.exit()
    ff=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{WD}x{HT}","-r",str(FPS),"-i","-","-i",f"{W_}/mix.wav","-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-af","loudnorm=I=-14:TP=-1.5","-shortest","-movflags","+faststart",f"{W_}/gold_tsumitate_short.mp4"],stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for b in pool.imap(frame,range(n),chunksize=8): ff.stdin.write(b)
    ff.stdin.close(); ff.wait(); print("done",n)
