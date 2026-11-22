// Rank calibration: for each play, evaluate a grid of throws the receivers can actually reach (both throw types) with the
// game's model, and record EPA minus the pro's EPA. A player "at quantile q" makes the q-th best of those throws every snap;
// the mean of that over plays is what an average 6-snap round at that skill scores per snap. Also: where the pro's own throw ranks.
// Usage: node tools/calibrate_ranks.js [highlights|season] [maxPlays]
const fs=require('fs'),path=require('path'),H=require('./model_harness.js');
const set=process.argv[2]||'highlights',max=+(process.argv[3]||400);
let plays=set==='season'?JSON.parse(fs.readFileSync(path.join(__dirname,'..','data','bdb_plays','index.json'))).map(e=>e[0]):null;
if(plays){for(let i=plays.length-1;i>0;i--){const j=(i*7919)%(i+1);[plays[i],plays[j]]=[plays[j],plays[i]];}plays=plays.slice(0,max).map(k=>JSON.parse(fs.readFileSync(path.join(__dirname,'..','data','bdb_plays',k+'.json'))));}
else plays=require('../real_plays.json').slice(0,max);
const Q=[.999,.99,.97,.95,.9,.85,.8,.7,.6,.5,.4,.3,.2,.1,.05];const acc=Q.map(()=>0);let proQ=0,n=0;
for(const r of plays){const x=H.evalPro(r),p=x.p,proE=x.ev.epa,vals=[];
  for(let sx=1;sx<=52;sx+=1.5)for(let sy=-3;sy<=50;sy+=1.5)for(const t of ['fast','touch']){const e=H.M.evaluate(p,{x:sx,y:sy},t);if(e.gr<=2)vals.push(e.epa-proE);}
  if(vals.length<10)continue;vals.sort((a,b)=>a-b);n++;
  Q.forEach((q,i)=>acc[i]+=vals[Math.min(vals.length-1,Math.floor(q*vals.length))]);proQ+=vals.filter(v=>v<0).length/vals.length;}
console.log(JSON.stringify({set,plays:n,proQuantile:+(proQ/n).toFixed(3),perSnap:Object.fromEntries(Q.map((q,i)=>[q,+(acc[i]/n).toFixed(3)]))}));
