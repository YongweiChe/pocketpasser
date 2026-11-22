import asyncio
from playwright.async_api import async_playwright
import os,pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
THREE=open(ROOT/'node_modules/three/build/three.module.min.js').read()
CASES=[('catch','complete','',3),('drop','incomplete','drop',0),('int','int','',0),('miss','incomplete','miss',0),('sack',None,None,0)]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg=await b.new_page(viewport={'width':1100,'height':640});errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.route('**/three.module.min.js',lambda r:r.fulfill(status=200,content_type='application/javascript',body=THREE))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto((ROOT/'beat-the-pro-qb-cam.html').as_uri());await pg.wait_for_timeout(2500)
    await pg.evaluate("localStorage.setItem('qbcam.visited','1')");await pg.click('#goPractice')
    for _ in range(40):
      if await pg.evaluate("!!(__S.round&&__S.round.kind)"):break
      await pg.wait_for_timeout(150)
    for name,kind,sub,yac in CASES:
      await pg.evaluate("__S.round.kind='practice';__load(__PLAYS.findIndex(p=>p.name==='Curl-flat with a seam'))");await pg.wait_for_timeout(300)
      await pg.evaluate("__S.limit="+("200" if name=='sack' else "0"));await pg.keyboard.press('Space')
      for i in range(80):
        if await pg.evaluate("__S.phase")=='decide':break
        await pg.wait_for_timeout(120)
      if name!='sack':
        await pg.evaluate(f"(()=>{{const pl=__PLAYS[__S.pi],r=pl.byId[pl.pro.target];__force(pl.pro.spot.x,pl.pro.spot.y,pl.pro.type,'{kind}','{sub}',{yac});}})()")
      for i in range(100):
        if await pg.evaluate("__S.phase")=='cine':break
        await pg.wait_for_timeout(80)
      for k,w in enumerate([450,500]):
        await pg.wait_for_timeout(w);await pg.screenshot(path=f'out_sl_{name}{k}.png')
      for i in range(60):
        if await pg.evaluate("__S.phase")=='done':break
        await pg.wait_for_timeout(150)
    print(errs[:4]);await b.close()
asyncio.run(main())
