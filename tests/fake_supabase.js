// fake supabase-js: session + tables in localStorage (shared across tabs), knobs on window.__fake
const L=localStorage,get=k=>JSON.parse(L.getItem(k)||'null'),put=(k,v)=>L.setItem(k,JSON.stringify(v));
const K='sb-fake-auth-token';
export function createClient(){
  const cbs=[];const F=window.__fake=window.__fake||{};
  const db=()=>get('fake.db')||{profiles:[],daily_scores:[],rounds:[],snaps:[]};
  const save=d=>put('fake.db',d);
  const auth={
    async getSession(){if(F.sessDelay)await new Promise(r=>setTimeout(r,F.sessDelay));const s=get(K);return{data:{session:s}};},
    onAuthStateChange(cb){cbs.push(cb);return{data:{subscription:{unsubscribe(){}}}};},
    async signOut(){L.removeItem(K);cbs.forEach(cb=>cb('SIGNED_OUT',null));return{error:null};},
    async signInWithOAuth(){return{data:{url:'about:blank#fake-google'},error:null};},
  };
  function q(t){const st={t,f:[],op:'select',row:null,lim:1e9,ord:null};
    const run=async()=>{const d=db();let rows=d[t]||[];const uid=(get(K)||{}).user?.id;
      if(st.op==='insert'){if(F.failInsert&&t==='daily_scores'){F.failInsert--;return{error:{code:'net'}};}
        if(t==='daily_scores'){if(!uid)return{error:{code:'42501'}};if(rows.some(r=>r.user_id===uid&&r.day===st.row.day))return{error:{code:'23505'}};
          const p=(d.profiles.find(p=>p.id===uid)||{});st.row={...st.row,user_id:uid,name:p.username||'Player',created_at:new Date().toISOString()};}
        else st.row={...st.row,user_id:uid,created_at:new Date().toISOString()};
        rows.push(st.row);d[t]=rows;save(d);return{error:null};}
      if(st.op==='upsert'){const lower=(st.row.username||'').toLowerCase();if(lower&&d.profiles.some(p=>p.id!==st.row.id&&(p.username||'').toLowerCase()===lower))return{error:{code:'23505'}};
        const i=d.profiles.findIndex(p=>p.id===st.row.id);if(i>=0)d.profiles[i]={...d.profiles[i],...st.row};else d.profiles.push(st.row);save(d);return{error:null};}
      rows=rows.filter(r=>st.f.every(([k,v])=>r[k]===v));if(t!=='daily_scores'&&t!=='profiles')rows=rows.filter(r=>r.user_id===uid);
      return{data:rows.slice(0,st.lim),error:null};};
    const o={select(){return o},eq(k,v){st.f.push([k,v]);return o},lte(){return o},order(){return o},limit(n){st.lim=n;return run()},
      insert(r){st.op='insert';st.row=r;return run()},upsert(r){st.op='upsert';st.row=r;return run()},
      async maybeSingle(){const r=await run();return{data:(r.data||[])[0]||null,error:null}},then(a,b){return run().then(a,b)}};
    return o;}
  return {auth,from:q,async rpc(fn,{name}){const d=db();const uid=(get(K)||{}).user?.id;return{data:/^[A-Za-z0-9_]{3,16}$/.test(name)&&!d.profiles.some(p=>p.id!==uid&&(p.username||'').toLowerCase()===name.toLowerCase()),error:null};}};
}
// test helper: "Google finished in the popup" = write the session + ping like auth.html does
window.__fakeSignIn=(id,full)=>{put(K,{user:{id,user_metadata:{full_name:full||'Test Player'}}});try{new BroadcastChannel('pp-auth').postMessage('signed-in');}catch(e){}};
