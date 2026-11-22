const {chromium}=require('playwright');const fs=require('fs');
const FPS=+process.env.FPS||30;const only=process.env.ONLY; // e.g. "5,30,60" seconds for previews
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:720},deviceScaleFactor:+(process.env.DSF||1)});
const errs=[];p.on('pageerror',e=>errs.push(e.message));
const TL=fs.readFileSync('timeline.json','utf8');
await p.addInitScript('window.TL='+TL);
await p.goto('file://'+process.cwd()+'/video.html');await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(800);
const total=JSON.parse(TL).total;
if(only){for(const s of only.split(',')){await p.evaluate(t=>renderAt(t),+s);await p.screenshot({path:`prev_${s}.png`});}console.log(errs);await b.close();return;}
fs.mkdirSync('frames',{recursive:true});
const N=Math.ceil(total*FPS);
for(let i=0;i<N;i++){await p.evaluate(t=>renderAt(t),i/FPS);await p.screenshot({path:`frames/f${String(i).padStart(5,'0')}.jpg`,type:'jpeg',quality:92});if(i%300===0)console.log(i,'/',N);}
console.log('errors',errs);await b.close();})();
