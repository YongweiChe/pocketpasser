"""Favicon (pixel football), apple touch icon and the link-preview image (og.png) -> site/. Run once; build.py copies site/ into public/."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = os.path.join(ROOT, 'site')
# 16x16 pixel football, tipped 45 degrees: . empty, B brown, D dark outline, W white stripe/laces
G = """
..........DDDD..
........DDBBBWD.
......DDBBBBBWWD
.....DBBBBBBBBWD
....DBBBBBWBBBBD
...DBBBBBWBWBBBD
..DBBBBBWBWBBBD.
.DBBBBBWBWBBBD..
.DBBBBWBWBBBBD..
DBBBBBBWBBBBD...
DBBBBBBBBBBD....
DWBBBBBBBBD.....
DWWBBBBBDD......
.DWBBBDD........
..DDDD..........
................""".split()
COL = {'B': (150, 82, 40), 'D': (60, 30, 14), 'W': (255, 255, 255)}
svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" shape-rendering="crispEdges">']
for y, row in enumerate(G):
    for x, ch in enumerate(row):
        if ch in COL: svg.append('<rect x="%d" y="%d" width="1" height="1" fill="#%02x%02x%02x"/>' % ((x, y) + COL[ch]))
open(os.path.join(SITE, 'favicon.svg'), 'w').write(''.join(svg) + '</svg>')
def icon(size, bg=None, pad=0):
    im = Image.new('RGBA', (16, 16), bg or (0, 0, 0, 0)); px = im.load()
    for y, row in enumerate(G):
        for x, ch in enumerate(row):
            if ch in COL: px[x, y] = COL[ch] + (255,)
    inner = size - 2 * pad; out = Image.new('RGBA', (size, size), bg or (0, 0, 0, 0))
    out.paste(im.resize((inner, inner), Image.NEAREST), (pad, pad)); return out
icon(32).save(os.path.join(SITE, 'favicon-32.png'))
icon(180, (7, 13, 24, 255), 22).convert('RGB').save(os.path.join(SITE, 'apple-touch-icon.png'))
# link preview: the route view from the trailer, a dark wash over the empty far field, the wordmark and the headline
fr = Image.open(os.path.join(ROOT, 'tools/trailer/frames2/s3_routes/0118.png')).convert('RGB').resize((1200, 675), Image.LANCZOS).crop((0, 45, 1200, 675))
wash = Image.new('RGBA', (1200, 630)); d = ImageDraw.Draw(wash)
for y in range(630): d.line([(0, y), (1200, y)], fill=(5, 9, 16, int(235 * max(0, 1 - y / 360) ** 1.2)))
im = Image.alpha_composite(fr.convert('RGBA'), wash); d = ImageDraw.Draw(im)
PIX = os.path.join(ROOT, 'tools/trailer/font/PressStart2P.ttf')
def text(t, size, y, col):
    f = ImageFont.truetype(PIX, size); b = f.getbbox(t); x = (1200 - (b[2] - b[0])) // 2 - b[0]; s = max(3, size // 10)
    d.text((x + s, y + s), t, font=f, fill=(0, 0, 0)); d.text((x, y), t, font=f, fill=col)
text('POCKET PASSER', 72, 58, (245, 197, 24))
text('THINK YOU CAN OUTREAD', 34, 168, (255, 255, 255)); text('AN NFL QUARTERBACK?', 34, 218, (255, 255, 255))
fb = icon(64); im.paste(fb, (1200 - 64 - 28, 630 - 64 - 24), fb)
im.convert('RGB').save(os.path.join(SITE, 'og.png'), optimize=True)
print('site/:', sorted(os.listdir(SITE)))
