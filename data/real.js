function realToPlay(r){
  const tr=f=>({type:'track',f}),pathOf=(f,T)=>{const p=[];for(let i=0;i<f.length;i+=3)if(f[i]<=T+.6)p.push([f[i+1],f[i+2]]);return p.length>1?p:[[f[1],f[2]],[f[1],f[2]+.01]];};
  const off=r.off.map(p=>({id:'o'+p.num,label:p.elig?p.pos+' '+p.num:p.pos,num:p.num,name:p.name,pos:p.pos,speed:p.speed||7,block:!p.elig,big:!p.elig,beh:Object.assign(tr(p.f),{path:pathOf(p.f,r.T)})}));
  const def=r.def.map(p=>({id:p.pos,key:'d'+p.num,label:p.pos,num:p.num,name:p.name,pos:p.pos,sprint:p.sprint,react:p.react,o:p.o,rush:p.rush,big:['DE','DT','NT','DL'].includes(p.pos),beh:tr(p.f)}));
  const tgt=off.find(o=>o.num===r.pro.targetNum&&!o.block)||off.find(o=>!o.block);
  return{real:true,meta:r,name:'Real NFL play',coverage:'the real defense',down:r.down,dist:r.dist,ytg:r.ytg,clock:r.clock,T:r.T,score:r.score,
    qb:{id:'QB',label:'QB',num:r.qb.num,name:r.qb.name,beh:tr(r.qb.f)},off,def,
    pro:{target:tgt.id,spot:r.pro.spot,type:r.pro.type,result:r.pro.result,text:r.pro.text},note:'What happened: '+r.pro.text};}
if(typeof module!=='undefined')module.exports={realToPlay};
