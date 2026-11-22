import asyncio,base64
from playwright.async_api import async_playwright
import os,pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
THREE=open(ROOT/'node_modules/three/build/three.module.min.js').read()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=await b.new_page()
    await pg.route('**/three.module.min.js',lambda r:r.fulfill(status=200,content_type='application/javascript',body=THREE))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto((ROOT/'beat-the-pro-qb-cam.html').as_uri());await pg.wait_for_timeout(2000)
    for st in ['sticker','flat','painted','pixel']:
      for side,num in (('off',14),('def',24)):
        u=await pg.evaluate(f"__atlas('{st}','{side}',{num})")
        open(f'out_at_{st}_{side}.png','wb').write(base64.b64decode(u.split(',')[1]))
    await b.close()
asyncio.run(main())
