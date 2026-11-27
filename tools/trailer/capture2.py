"""Trailer v2 capture (storyboard: push-in over the routes, memorize, drop into the QB's slot, the freeze, the catch
running straight into the win banner, the replay view). Fake page clock stepped 1/30 s per frame; CSS animations scrubbed
to the same virtual time. Usage: python3 tools/trailer/capture2.py   (needs the local server on :8000)"""
import os, shutil
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'frames2v' if '--portrait' in __import__('sys').argv else 'frames2')
FPS = 30; DT = 1000 / FPS
import sys; PUSH_ONLY = '--push-only' in sys.argv; PORTRAIT = '--portrait' in sys.argv
KEY = '2019_BAL_2019090803_683'          # Lamar Jackson to Marquise Brown, 83 yd TD (public highlight)
BEST = [22.5, 38, 'fast']                # the model's best read on this play
SYNC = "(()=>{const now=performance.now();for(const a of document.getAnimations()){if(a.__t0==null){a.__t0=now;a.pause();}a.currentTime=now-a.__t0;}})()"
CLEAN = """#controls,#help,#banner,#badge,#sit,.escHint,#mute,#prog,#nextHint,#res,#skipHint{display:none!important}
body.trailer-quiet #cd{display:none!important}"""
# push-in: from high above and behind the stadium down onto the normal route view (eased), then hand back to the game camera
PUSH = """(()=>{let end=null,t0=null,snapAt=null;const D=window.__pushMs,OFF=window.__camOff||[0,0,0];window.__camOv=(cam,now)=>{
  const V3=cam.position.constructor,off=new V3(OFF[0],OFF[1],OFF[2]);
  if(!end){end={p:cam.position.clone().add(off),q:cam.quaternion.clone()};const f=new V3(0,0,-1).applyQuaternion(end.q);
    end.look=end.p.clone().add(f.multiplyScalar(40));end.s=end.p.clone().add(new V3(0,46,38));t0=now;}
  const u=Math.min(1,(now-t0)/D),k=u*u*(3-2*u);/* slow in, slow out */
  if(u<1){cam.position.lerpVectors(end.s,end.p,k);cam.lookAt(end.look);if(k>.97)cam.quaternion.slerp(end.q,(k-.97)/.03);return;}
  /* after the push: keep the (portrait) offset on the game camera, easing it out over 0.7 s once the ball is snapped */
  if(window.__S.phase!=='pre'&&snapAt==null)snapAt=now;const g=snapAt==null?1:Math.max(0,1-(now-snapAt)/700);
  if(g<=0||!OFF.some(Boolean)){window.__camOv=null;return;}cam.position.add(off.multiplyScalar(g*g*(3-2*g)));};})()"""

def main():
    if PUSH_ONLY: shutil.rmtree(os.path.join(OUT, 's12_push'), ignore_errors=True)
    else: shutil.rmtree(OUT, ignore_errors=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        ctx = (b.new_context(viewport={'width': 720, 'height': 1280}, device_scale_factor=1.5, has_touch=True, is_mobile=True) if PORTRAIT
               else b.new_context(viewport={'width': 1280, 'height': 720}, device_scale_factor=1.5))
        pg = ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.clock.install(); pg.goto('http://localhost:8000/fp2.html', timeout=180000)
        pg.evaluate("localStorage.setItem('qbcam.visited','1');localStorage.setItem('qbcam.sound','0')")
        pg.clock.pause_at(pg.evaluate("Date.now()") + 200)
        tick = lambda ms=DT: pg.clock.run_for(int(ms))
        def until(cond, limit=90000, step=100):
            t = 0
            while not pg.evaluate(cond):
                tick(step); t += step
                if t > limit: raise RuntimeError('timeout: ' + cond)
        def shoot(seg, frames, each=None, stop=None):
            d = os.path.join(OUT, seg); os.makedirs(d, exist_ok=True)
            for f in range(frames):
                if stop and pg.evaluate(stop): break
                if each: each(f)
                pg.evaluate(SYNC); pg.screenshot(path=os.path.join(d, '%04d.png' % f)); tick()
            print(seg, len(os.listdir(d)), 'frames', flush=True)

        until("window.__PLAYS&&__PLAYS.length>5"); pg.add_style_tag(content=CLEAN)
        idx = pg.evaluate(f"__PLAYS.findIndex(p=>p.real&&p.meta.key==='{KEY}')")
        pg.click('#goPractice'); until("__S.round&&__S.phase==='pre'")
        pg.evaluate(f"document.body.classList.add('trailer-quiet');__load({idx});__S.memoEnd=performance.now()+1e7;__S.limit=6000")
        tick(1500)                                   # let the auto down-and-distance flash pass off camera
        # shots 1-2: push-in onto the field and the routes (titles are added in compose)
        pg.evaluate("(()=>{const e=document.getElementById('ddFlash');clearTimeout(e._d);clearTimeout(e._t);e.innerHTML='';})()")   # no stray down-and-distance flash during the push
        pg.evaluate("window.__pushMs=6000;window.__camOff=" + ("[0,9,15]" if PORTRAIT else "[0,0,0]") + ";" + PUSH); tick()   # first frame already on the start pose
        shoot('s12_push', 210)
        if PUSH_ONLY: print('errors:', errs[:3]); b.close(); return
        # shot 3: route view, the down-and-distance flash punches in
        shoot('s3_routes', 120, each=lambda f: f == 8 and pg.evaluate("__ddFlash()"))
        # shot 4: memorize the routes, countdown visible
        pg.evaluate("document.body.classList.remove('trailer-quiet');__S.memoEnd=performance.now()+4300"); tick()   # one frame so the countdown redraws before the first shot
        shoot('s4_memorize', 120)
        # shots 5-6: snap -> the camera drops into the QB's eyes -> dropback, a look left and back
        pg.keyboard.press('Space')
        def look(f):
            if f == 62: pg.keyboard.press('1')
            if f == 92: pg.keyboard.press('2')
        shoot('s56_drop', 200, each=look, stop="__S.phase==='decide'")
        # shot 7: the freeze, the aim ring drifting onto the open receiver
        start = pg.evaluate("(()=>{const pl=__PLAYS[__S.pi];return [pl.pro.spot.x-9,pl.pro.spot.y-12]})()")
        def aim(f):
            u = min(1, f / 55); k = 1 - (1 - u) ** 3
            pg.evaluate(f"__S.aim={{x:{start[0] + (BEST[0] - start[0]) * k},y:{start[1] + (BEST[1] - start[1]) * k}}}")
        shoot('s7_freeze', 90, each=aim)
        # shot 8 -> 9: the throw, the catch, the replay running straight into the win banner (no cut)
        pg.evaluate(f"__S.aim=null;(()=>{{const pl=__PLAYS[__S.pi];__force({BEST[0]},{BEST[1]},'{BEST[2]}','complete',null,Math.max(0,pl.ytg-{round(BEST[1])}));}})()")
        shoot('s8_catch', 700, stop="document.getElementById('flash').classList.contains('on')")
        shoot('s9_banner', 110, stop="__S.reviewOn")
        until("__S.reviewOn", 8000, 33)
        # shot 10: the replay view
        shoot('s10_review', 100)
        print('errors:', errs[:3]); b.close()

if __name__ == '__main__':
    main()
