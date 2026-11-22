// For every full-season play (data/bdb_plays), evaluate the pro's real throw with the game's model and write the
// model's inputs + its current (hand-tuned) odds + what actually happened -> CSV for tools/fit_completion.py.
const fs=require('fs'),path=require('path'),H=require('./model_harness.js');
const dir=path.join(__dirname,'..','data','bdb_plays'),out=process.argv[2];
const idx=JSON.parse(fs.readFileSync(path.join(dir,'index.json')));
const rows=['key,week,result,gr,gd,behind,lane,fl,d,depth,fast,target_hit,hand_pC,hand_pI'];let bad=0;
for(const e of idx){try{const r=JSON.parse(fs.readFileSync(path.join(dir,e[0]+'.json'))),x=H.evalPro(r),v=x.ev;
  const tgt=x.p.pro.target,hit=v.r&&v.r.id===tgt?1:0;
  rows.push([e[0],e[7],x.kind,v.gr.toFixed(3),v.gd.toFixed(3),v.behind?1:0,v.lane.toFixed(4),v.fl.toFixed(3),x.d.toFixed(2),v.S.y.toFixed(2),v.type==='fast'?1:0,hit,v.pC.toFixed(4),v.pI.toFixed(4)].join(','));}
  catch(err){bad++;}}
fs.writeFileSync(out,rows.join('\n'));console.log('rows',rows.length-1,'failed',bad);
