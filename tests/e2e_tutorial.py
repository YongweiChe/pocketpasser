import asyncio
from playwright.async_api import async_playwright
import os,pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
THREE=open(ROOT/'node_modules/three/build/three.module.min.js').read()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg=await b.new_page(viewport={'width':1280,'height':760});errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.route('**/three.module.min.js',lambda r:r.fulfill(status=200,content_type='application/javascript',body=THREE))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto((ROOT/'beat-the-pro-qb-cam.html').as_uri());await pg.wait_for_timeout(2500);await pg.screenshot(path='out_m0.png')
    await pg.click('#tutBtn');await pg.wait_for_timeout(1200);await pg.screenshot(path='out_m1.png');await pg.keyboard.press('Space')
    for i in range(80):
      if await pg.evaluate("__S.phase")=='decide':break
      await pg.wait_for_timeout(150)
    await pg.wait_for_timeout(400);await pg.mouse.move(700,330);await pg.wait_for_timeout(400);await pg.screenshot(path='out_m2.png')
    for i in range(600):
      ph,ri=await pg.evaluate("[__S.phase,__S.round.i]")
      if ph=='results':break
      if ph=='pre' or ph=='done':await pg.keyboard.press('Space')
      if ph=='decide':
        pt=await pg.evaluate('__pathPt(0,13)')
        if pt: await pg.mouse.click(pt[0],pt[1])
        else: await pg.keyboard.down('Shift');await pg.mouse.click(640,330);await pg.keyboard.up('Shift')
      await pg.wait_for_timeout(200)
    print(await pg.evaluate("[__S.phase,document.querySelector('#again').textContent,document.querySelector('#rsKind').textContent]"))
    await pg.screenshot(path='out_m3.png')
    await pg.evaluate("document.querySelector('#again').click()");await pg.wait_for_timeout(500)
    print(await pg.evaluate("[__S.round.kind,__S.limit,__S.routes,document.querySelector('#routesBtn').disabled,document.querySelector('#tut').hidden]"))
    print(errs[:5]);await b.close()
asyncio.run(main())
