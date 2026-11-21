const {chromium}=require('playwright');const fs=require('fs');const {spawn}=require('child_process');
(async()=>{
  const px=process.env.HTTPS_PROXY||process.env.https_proxy;
  const b=await chromium.launch(px?{proxy:{server:px}}:{});
  const ctx=await b.newContext({viewport:{width:1080,height:1920},ignoreHTTPSErrors:true});const p=await ctx.newPage();
  p.on('pageerror',e=>console.error('PAGEERR',e.message));
  await p.goto('file://'+__dirname+'/scene.html');
  const lines=JSON.parse(fs.readFileSync('script.json')),durs=JSON.parse(fs.readFileSync('durations.json'));
  const total=await p.evaluate(([l,d])=>setup(l,d),[lines,durs]);
  await p.evaluate(async()=>{await document.fonts.load("800 50px 'M PLUS Rounded 1c'", 'あ耳鼻科四国めたん霧');await document.fonts.load("500 50px 'M PLUS Rounded 1c'",'あ');await document.fonts.ready});
  console.log('fontok',await p.evaluate(()=>document.fonts.check("800 50px 'M PLUS Rounded 1c'")),'total',total);
  const mode=process.argv[2];
  if(mode==='preview'){const ts=process.argv.slice(3).map(Number);fs.mkdirSync('preview',{recursive:true});
    for(const t of ts){await p.evaluate(t=>render(t),t);await p.screenshot({path:`preview/t${t}.png`})}}
  else{const fps=30,N=Math.ceil(total*fps);
    const ff=spawn('ffmpeg',['-y','-f','image2pipe','-framerate',''+fps,'-c:v','mjpeg','-i','-','-i','audio/full.wav','-c:v','libx264','-pix_fmt','yuv420p','-preset','medium','-crf','20','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart','nebulizer_short.mp4'],{stdio:['pipe','inherit','inherit']});
    for(let f=0;f<N;f++){await p.evaluate(t=>render(t),f/fps);const buf=await p.screenshot({type:'jpeg',quality:93});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));if(f%300==0)console.log('frame',f,'/',N)}
    ff.stdin.end();await new Promise(r=>ff.on('close',r))}
  await b.close()})();
