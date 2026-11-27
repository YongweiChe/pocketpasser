"""Account state machine: sign-in, the 2-round guest wall, claiming a Today's 6 spot, usernames, sign-out, retries.
Uses a fake Supabase (tests/fake_supabase.js served in place of supabase-js) so timing, sessions and failures are controlled.
Run with the local server on :8000:  python3 tests/e2e_accounts.py   (expects 12/12 passed)"""
import os
from playwright.sync_api import sync_playwright
FAKE=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'fake_supabase.js')).read()
URL='http://localhost:8000/fp2.html'
FIN="""(()=>{const r=__S.round;r.res=r.plays.map((x,i)=>({diff:[.42,-.18,.31,.05,-.2,.36][i],mine:1,pro:.6,sit:'1st & 10',who:'Lamar Jackson',opp:'Dolphins',desc:'',real:true}));__showResults();})()"""
res=[]
def check(name,cond,detail=''):
    res.append((name,bool(cond)));print(('PASS ' if cond else 'FAIL ')+name+('' if cond else '  -> '+str(detail)),flush=True)
with sync_playwright() as p:
    b=p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    def fresh(init_js='',seed=None):
        ctx=b.new_context(viewport={'width':1280,'height':900})
        ctx.route('**/supabase-js@2.45.4/+esm',lambda r:r.fulfill(status=200,content_type='application/javascript',body=FAKE))
        ctx.add_init_script("if(!sessionStorage.getItem('__seeded')&&!localStorage.getItem('__seeded')){localStorage.setItem('__seeded','1');localStorage.setItem('qbcam.visited','1');"+init_js+"}else{window.__fake=window.__fake||{};}")
        pg=ctx.new_page();pg.errs=[];pg.on('pageerror',lambda e:pg.errs.append(str(e)))
        return ctx,pg
    def popup_signin(ctx,uid='u1',full='Test Player'):
        o=ctx.new_page();o.goto(URL,wait_until='domcontentloaded');o.evaluate(f"__fakeSignIn('{uid}','{full}')");o.close()
    def wait(pg,cond,ms=8000):
        for _ in range(ms//200):
            if pg.evaluate(cond):return True
            pg.wait_for_timeout(200)
        return False
    def state(pg):return pg.evaluate("({user:__AUTH.user&&__AUTH.user.id,name:__AUTH.name,round:__S.round&&__S.round.kind,phase:__S.phase,wall:!document.getElementById('wall').hidden,un:!document.getElementById('unSheet').hidden,guest:localStorage.getItem('qbcam.guestRounds')})")
    SEED_USER="localStorage.setItem('sb-fake-auth-token',JSON.stringify({user:{id:'u1',user_metadata:{full_name:'Test Player'}}}));localStorage.setItem('fake.db',JSON.stringify({profiles:[{id:'u1',username:'TestQB'}],daily_scores:[],rounds:[],snaps:[]}));"

    # 1. signed-in player clicks Play while the session is still loading: not counted as a guest round, no wall
    ctx,pg=fresh(SEED_USER+"window.__fake={sessDelay:2500};")
    pg.goto(URL);pg.wait_for_selector('#go',state='visible');pg.click('#go');wait(pg,"!!(__S.round)",9000);s=state(pg)
    check('1 signed-in, click during auth load: no guest count, no wall',s['user']=='u1' and not s['wall'] and s['guest'] in (None,'0'),s);ctx.close()

    # 2. guest who used both free rounds clicks Play during auth load: walled
    ctx,pg=fresh("localStorage.setItem('qbcam.guestRounds','2');window.__fake={sessDelay:2500};")
    pg.goto(URL);pg.wait_for_selector('#go',state='visible');pg.click('#go');wait(pg,"!document.getElementById('wall').hidden",9000);s=state(pg)
    check('2 exhausted guest, click during auth load: wall',s['wall'] and not s['round'],s);ctx.close()

    # 3. wall -> Not now -> later sign in from the corner: no surprise round
    ctx,pg=fresh("localStorage.setItem('qbcam.guestRounds','2');localStorage.setItem('fake.db',JSON.stringify({profiles:[{id:'u1',username:'TestQB'}],daily_scores:[],rounds:[],snaps:[]}));")
    pg.goto(URL);wait(pg,"__AUTH.settled");pg.click('#goPractice');wait(pg,"!document.getElementById('wall').hidden");pg.click('#wallHome');pg.wait_for_timeout(500)
    popup_signin(ctx);wait(pg,"__AUTH.name==='TestQB'");pg.wait_for_timeout(1500);s=state(pg)
    check('3 abandoned wall, later sign-in: stays home',s['user']=='u1' and not s['round'] and not s['wall'],s);ctx.close()

    # 4. wall -> popup sign-in that cannot message back -> the round starts
    ctx,pg=fresh("localStorage.setItem('qbcam.guestRounds','2');localStorage.setItem('fake.db',JSON.stringify({profiles:[{id:'u1',username:'TestQB'}],daily_scores:[],rounds:[],snaps:[]}));")
    pg.goto(URL);wait(pg,"__AUTH.settled");pg.click('#goPractice');wait(pg,"!document.getElementById('wall').hidden");pg.click('#wallGo');pg.wait_for_timeout(500)
    popup_signin(ctx);ok=wait(pg,"__S.round&&__S.round.kind==='practice'",10000);s=state(pg)
    check('4 wall + cut-off popup: practice round starts',ok and not s['wall'],s);ctx.close()

    # 5. new player: wall -> sign in -> username box -> pick -> round starts (only after the name)
    ctx,pg=fresh("localStorage.setItem('qbcam.guestRounds','2');")
    pg.goto(URL);wait(pg,"__AUTH.settled");pg.click('#goPractice');wait(pg,"!document.getElementById('wall').hidden");pg.click('#wallGo');pg.wait_for_timeout(300)
    popup_signin(ctx,'u2','New Person');wait(pg,"!document.getElementById('unSheet').hidden");before=state(pg)
    pg.fill('#unIn','NewPerson7');wait(pg,"!document.getElementById('unGo').disabled");pg.click('#unGo');ok=wait(pg,"__S.round&&__S.round.kind==='practice'",10000)
    check('5 new player: round waits for the username, then starts',before['un'] and not before['round'] and ok,before);ctx.close()

    # 6. guest claims Today's 6 via popup -> posted on the results page
    ctx,pg=fresh("localStorage.setItem('fake.db',JSON.stringify({profiles:[{id:'u1',username:'TestQB'}],daily_scores:[],rounds:[],snaps:[]}));")
    pg.goto(URL);wait(pg,"__AUTH.settled");pg.click('#go');wait(pg,"!!__S.round");pg.evaluate(FIN);wait(pg,"!!document.getElementById('rsClaim')")
    pg.click('#rsClaim');popup_signin(ctx);ok=wait(pg,"/Posted to today/.test(document.getElementById('rsNote').textContent)",10000)
    check('6 guest claim via cut-off popup: posted',ok,pg.inner_text('#rsNote'));ctx.close()

    # 7. claim with the popup blocked -> full redirect -> back on the page -> posted, board opens
    ctx,pg=fresh("localStorage.setItem('fake.db',JSON.stringify({profiles:[{id:'u1',username:'TestQB'}],daily_scores:[],rounds:[],snaps:[]}));")
    pg.goto(URL);wait(pg,"__AUTH.settled");pg.click('#go');wait(pg,"!!__S.round");pg.evaluate(FIN);wait(pg,"!!document.getElementById('rsClaim')")
    pg.evaluate("window.open=()=>null");pg.click('#rsClaim');pg.wait_for_timeout(800)
    pend=pg.evaluate("sessionStorage.getItem('qbcam.pending')")
    pg.evaluate("localStorage.setItem('sb-fake-auth-token',JSON.stringify({user:{id:'u1',user_metadata:{full_name:'T'}}}))");pg.goto(URL)
    ok=wait(pg,"!document.getElementById('boardSheet').hidden&&/Posted to today/.test(document.getElementById('hbNote').textContent)",10000)
    rounds=pg.evaluate("JSON.parse(localStorage.getItem('fake.db')).rounds.length")
    check('7 claim with popup blocked: redirect, then posted and board shown; no duplicate round saved',pend and ok and rounds==0,(pend,pg.inner_text('#hbNote') if pg.is_visible('#hbNote') else None,rounds));ctx.close()

    # 8. sign out while the username box is open: box closes, nothing hangs
    ctx,pg=fresh("localStorage.setItem('sb-fake-auth-token',JSON.stringify({user:{id:'u3',user_metadata:{full_name:'No Name'}}}));")
    pg.goto(URL);wait(pg,"!document.getElementById('unSheet').hidden");pg.evaluate("__AUTH.client.auth.signOut()");pg.wait_for_timeout(800);s=state(pg)
    check('8 sign out with the username box open: box closes',not s['un'] and s['user'] is None,s);ctx.close()

    # 9. guest's second Today's 6 run of the day: no claim offered
    ctx,pg=fresh()
    pg.goto(URL);wait(pg,"__AUTH.settled");pg.click('#go');wait(pg,"!!__S.round");pg.evaluate(FIN);wait(pg,"!!document.getElementById('rsClaim')")
    pg.click('#rsHome');pg.wait_for_timeout(500);pg.click('#go');wait(pg,"__S.round&&__S.phase!=='results'");pg.evaluate(FIN);pg.wait_for_timeout(1500)
    check('9 guest second run: not claimable',not pg.is_visible('#rsClaim') and 'first run' in pg.inner_text('#rsNote'),pg.inner_text('#rsNote'));ctx.close()

    # 10. posting fails once -> Try again -> posted
    ctx,pg=fresh(SEED_USER+"window.__fake={failInsert:1};")
    pg.goto(URL);wait(pg,"__AUTH.name==='TestQB'");pg.click('#go');wait(pg,"!!__S.round");pg.evaluate(FIN);ok1=wait(pg,"!!document.getElementById('rsRetry')")
    pg.click('#rsRetry');ok2=wait(pg,"/Posted to today/.test(document.getElementById('rsNote').textContent)")
    check('10 post fails then retry: posted',ok1 and ok2,pg.inner_text('#rsNote'));ctx.close()

    # 11. sign out, play as guest, claim with an account that already posted today: clear message
    ctx,pg=fresh(SEED_USER)
    pg.goto(URL);wait(pg,"__AUTH.name==='TestQB'");pg.click('#go');wait(pg,"!!__S.round");pg.evaluate(FIN);wait(pg,"/Posted to today/.test(document.getElementById('rsNote').textContent)")
    pg.click('#rsHome');pg.evaluate("__AUTH.client.auth.signOut()");pg.wait_for_timeout(500)
    pg.evaluate("localStorage.removeItem('qbcam.dailyDone')")   # pretend this is the device's first run (e.g. other device posted)
    pg.click('#go');wait(pg,"__S.round&&__S.phase!=='results'");pg.evaluate(FIN);wait(pg,"!!document.getElementById('rsClaim')");pg.click('#rsClaim');popup_signin(ctx)
    ok=wait(pg,"/already on the board/.test(document.getElementById('rsNote').textContent)",10000)
    check('11 already posted on the account: says so',ok,pg.inner_text('#rsNote'));ctx.close()

    # 12. signed-in player on a device where another account posted today: still posts
    ctx,pg=fresh(SEED_USER+"localStorage.setItem('qbcam.daily.uOTHER',JSON.stringify('x'));")
    pg.goto(URL);wait(pg,"__AUTH.name==='TestQB'");pg.evaluate("(()=>{const d=new Date();localStorage.setItem('qbcam.daily.uOTHER',d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'))})()")
    pg.click('#go');wait(pg,"!!__S.round");pg.evaluate(FIN);ok=wait(pg,"/Posted to today/.test(document.getElementById('rsNote').textContent)")
    check('12 another account posted on this device: this one still posts',ok,pg.inner_text('#rsNote'));ctx.close()
    b.close()
print(f"\n{sum(r for _,r in res)}/{len(res)} passed")
