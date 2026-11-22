// Loads the game's shared model (index.html, the same region build.py splices into the 3D game) into Node,
// so scripts can evaluate real plays with exactly the game's catch / INT / EPA logic.
// Usage: const M=require('./tools/model_harness.js'); M.evalPro(playJson) etc.
const fs=require('fs'),path=require('path'),vm=require('vm');
const ROOT=path.join(__dirname,'..');
const ix=fs.readFileSync(process.env.MODEL_HTML||path.join(ROOT,'index.html'),'utf8');   // MODEL_HTML: evaluate another copy (e.g. the old model)
const ms=ix.indexOf('const W=53.33'),endTok='  return{cells,best};\n}',me=ix.indexOf(endTok,ms)+endTok.length;
if(ms<0||me<endTok.length)throw new Error('model region not found in index.html');
const {realToPlay}=require(path.join(ROOT,'data','real.js'));
const ctx={Math,JSON,console,Object,Array,Number,Infinity,isNaN};vm.createContext(ctx);
vm.runInContext(ix.slice(ms,me)+'\n;globalThis.__M={evaluate,heatmap,EP,epAfter,pos,prepPlay,qbOf,cpOdds:typeof cpOdds==="undefined"?null:cpOdds};',ctx);
const M=ctx.__M;
function load(r){const p=realToPlay(r);M.prepPlay(p);return p;}
// the model's read of the pro's actual throw + what really happened
function evalPro(r){const p=load(r),ev=M.evaluate(p,r.pro.spot,r.pro.type),qb=ev.qb;
  return{p,ev,kind:r.pro.result.kind,d:Math.hypot(r.pro.spot.x-qb.x,r.pro.spot.y-qb.y)};}
module.exports={M,load,evalPro};
