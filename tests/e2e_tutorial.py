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
    # first visit: the main button asks about the tutorial; yes = one real play with four centred cards, then today's 6
    await pg.click('#go');await pg.wait_for_timeout(300);await pg.click('#fqYes');await pg.wait_for_timeout(1200)
    cards=[await pg.evaluate("__S.tutCard")];await pg.screenshot(path='out_m1.png');await pg.keyboard.press('Space');await pg.wait_for_timeout(300);await pg.keyboard.press('Space')
    for i in range(80):
      if await pg.evaluate("__S.phase")=='decide':break
      await pg.wait_for_timeout(150)
    await pg.wait_for_timeout(400);cards.append(await pg.evaluate("__S.tutCard"));await pg.screenshot(path='out_m2.png');await pg.keyboard.press('Enter');await pg.wait_for_timeout(300)
    pt=await pg.evaluate('__pathPt(0,13)')
    if pt: await pg.mouse.click(pt[0],pt[1])
    else: await pg.keyboard.down('Shift');await pg.mouse.click(640,330);await pg.keyboard.up('Shift')
    for i in range(120):
      if await pg.evaluate("__S.tutCard")=='done':break
      if await pg.evaluate("__S.phase")!='done':await pg.keyboard.press('Space')
      await pg.wait_for_timeout(200)
    cards.append(await pg.evaluate("__S.tutCard"));await pg.screenshot(path='out_m3.png')
    await pg.keyboard.press('Space');await pg.wait_for_timeout(800)
    print(cards,await pg.evaluate("[__S.round.kind,__S.round.plays.every(i=>__PLAYS[i].real),__S.routes,document.querySelector('#tut').hidden]"))
    print(errs[:5]);await b.close()
asyncio.run(main())
