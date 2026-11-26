"""Capture real Pocket Passer gameplay frame by frame for the trailer.
The page clock is faked (Playwright clock) and stepped 1/30 s per frame; CSS animations are paused and scrubbed to the same
virtual time, so the footage is smooth 30 fps even though the software renderer is slow."""
import os, sys, time
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames')
FPS = 30; DT = 1000 / FPS
KEY = '2019_BAL_2019090803_683'          # Lamar Jackson to Marquise Brown, 83 yd TD

SYNC = """(()=>{const now=performance.now();for(const a of document.getAnimations()){if(a.__t0==null){a.__t0=now;a.pause();}a.currentTime=now-a.__t0;}})()"""

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        ctx = b.new_context(viewport={'width': 1280, 'height': 720}, device_scale_factor=1.5)
        pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.clock.install()
        pg.goto('http://localhost:8000/fp2.html', timeout=180000)
        pg.evaluate("localStorage.setItem('qbcam.visited','1');localStorage.setItem('qbcam.sound','0')")
        pg.clock.pause_at(pg.evaluate("Date.now()") + 200)   # time only moves when we step it

        def tick(ms=DT): pg.clock.run_for(int(ms))
        def until(cond, limit_ms=60000, step=100):
            t = 0
            while not pg.evaluate(cond):
                tick(step); t += step
                if t > limit_ms: raise RuntimeError('timeout waiting for ' + cond)
        n = {'k': 0}
        def shoot(seg, frames, each=None, stop=None):
            d = os.path.join(OUT, seg); os.makedirs(d, exist_ok=True)
            for f in range(frames):
                if stop and pg.evaluate(stop): frames = f; break
                if each: each(f)
                pg.evaluate(SYNC)
                pg.screenshot(path=os.path.join(d, '%04d.png' % f))
                tick()
            print(seg, len(os.listdir(d)), 'frames', flush=True)

        until("window.__PLAYS&&__PLAYS.length>5")
        pg.add_style_tag(content="#skipHint,.escHint{display:none!important}")   # cleaner shots
        idx = pg.evaluate(f"__PLAYS.findIndex(p=>p.real&&p.meta.key==='{KEY}')")
        pg.click('#goPractice'); until("__S.round&&__S.phase==='pre'")

        best=[22.5,38,'fast']   # the model's best read on this play (from a dry run)
        # 1. the route view + down & distance flash
        pg.evaluate(f"__S.results={{}};__S.round.res=[];__load({idx})"); tick(50)
        shoot('01_routes', 95)
        # 2. snap and the dropback, glancing left then back to the middle
        print('before snap', pg.evaluate("[__S.phase,__S.pi,__PLAYS[__S.pi].T]"), flush=True)
        pg.keyboard.press('Space')
        T = pg.evaluate("__PLAYS[__S.pi].T"); print('after snap', pg.evaluate("[__S.phase,__S.pi,+__S.t.toFixed(2)]"), flush=True)
        def look(f):
            if f == 34: pg.keyboard.press('1')
            if f == 62: pg.keyboard.press('2')
        shoot('02_drop', int(T * FPS) + 4, look)
        print('after drop', pg.evaluate("[__S.phase,__S.pi,+__S.t.toFixed(2),!!__S.paused,__S.tutCard]"), flush=True)
        until("__S.phase==='decide'", 5000)
        # 3. the freeze: aim drifts onto the best spot, then the throw
        shoot('03_freeze', 24)
        pg.evaluate(f"(()=>{{const pl=__PLAYS[__S.pi];__force({best[0]},{best[1]},'{best[2]}','complete',null,Math.max(0,pl.ytg-Math.round({best[1]})));}})()")   # caught and taken to the house
        # 4. ball in the air, catch cutscene, the win banner with confetti
        shoot('04_catch', 600, stop="document.getElementById('flash').classList.contains('on')")
        shoot('05_banner', 75)
        until("__S.reviewOn", 8000, 33)
        shoot('06_review', 60)

        # 5. results page (sample round shaped like a real one)
        pg.evaluate("""(()=>{const r=__S.round;r.res=r.plays.map((x,i)=>({title:'',desc:'',diff:[.42,-.18,.31,.05,-.2,.36][i],mine:[1.1,.2,.9,.4,-.1,1.3][i],pro:[.68,.38,.59,.35,.1,.94][i],
          sit:['1st & 10','3rd & 6','2nd & 4','1st & 10','3rd & 9','2nd & 7'][i],who:['Lamar Jackson','Patrick Mahomes','Drew Brees','Josh Allen','Aaron Rodgers','Dak Prescott'][i],opp:['Dolphins','Rams','Colts','Jets','Bears','Eagles'][i],
          real:true,thrown:true,kind:'complete',pC:.7,pI:.02,air:12,type:'fast',early:0,proPC:.7,proPI:.02,proAir:12,proType:'fast',proKind:'complete',proText:''}));__showResults();})()""")
        tick(400); shoot('07_results', 50)

        # 6. Drew Bledsoe mode: the newspaper hits the table
        pg.evaluate("document.getElementById('results').hidden=true;document.body.classList.remove('resultsOn')")
        pg.evaluate("document.getElementById('goBled').click()")
        shoot('08_bledsoe', 66)
        print('errors:', errs[:3]); b.close()

if __name__ == '__main__':
    main()
