"""Cut the captured gameplay into a fast trailer: punchy pixel title cards, captions on the footage, flash cuts, music."""
import os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FR, OUT = os.path.join(HERE, 'frames'), os.path.join(HERE, 'out')
W, H, FPS = 1920, 1080, 30
PIX = os.path.join(HERE, 'font', 'PressStart2P.ttf'); TXT = os.path.join(HERE, 'font', 'VT323.ttf')
GOLD, WHITE, GREEN = (245, 197, 24), (255, 255, 255), (74, 222, 128)
MUSIC = '/Users/yongweiche/pro_qb/audio/music/home.mp3'
DEST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'pocket-passer-trailer.mp4')

frames = []   # list of PIL images (kept as paths/lambdas would be leaner; 800 frames at 1080p is fine in memory as files)
n = 0
def emit(img):
    global n
    img.convert('RGB').save(os.path.join(OUT, '%05d.png' % n)); n += 1

def text_img(lines):
    """lines: [(text, size, color)] -> transparent image of the stacked lines with a hard pixel shadow"""
    fonts = [ImageFont.truetype(PIX, s) for _, s, _ in lines]
    sizes = [f.getbbox(t) for (t, _, _), f in zip(lines, fonts)]
    w = max(b[2] - b[0] for b in sizes) + 40; gap = 34
    h = sum(b[3] - b[1] for b in sizes) + gap * (len(lines) - 1) + 40
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); y = 10
    for (t, s, c), f, b in zip(lines, fonts, sizes):
        tw = b[2] - b[0]; x = (w - tw) // 2 - b[0]; sh = max(4, s // 9)
        d.text((x + sh, y - b[1] + sh), t, font=f, fill=(0, 0, 0, 255)); d.text((x, y - b[1]), t, font=f, fill=c + (255,))
        y += b[3] - b[1] + gap
    return im

def bg_card(seed=0):
    im = Image.new('RGB', (W, H), (8, 12, 20)); d = ImageDraw.Draw(im)
    for x in range(0, W, 96): d.line([(x, 0), (x, H)], fill=(14, 22, 34), width=2)   # faint yard-line grid
    return im

def card(lines, frames_n, bg=None):
    t = text_img(lines)
    for f in range(frames_n):
        base = (bg.copy() if bg is not None else bg_card())
        k = [1.9, 1.35, .94, 1.03, 1.0][f] if f < 5 else 1.0          # punch in: big -> overshoot -> settle
        tw, th = int(t.width * k), int(t.height * k)
        ti = t.resize((tw, th), Image.NEAREST)
        if f < 2: ti.putalpha(ti.getchannel('A').point(lambda a: int(a * (0.5 + 0.25 * f))))
        base.paste(ti, ((W - tw) // 2, (H - th) // 2), ti); emit(base)

def footage(seg, a, b, caption=None, cap_from=0, flash_in=True, fix=None):
    files = sorted(os.listdir(os.path.join(FR, seg)))[a:b]
    cap = text_img(caption) if caption else None
    for i, fn in enumerate(files):
        im = Image.open(os.path.join(FR, seg, fn)).convert('RGB').resize((W, H), Image.LANCZOS)
        if fix: fix(im)
        if flash_in and i < 2:   # white flash cut
            im = Image.blend(im, Image.new('RGB', (W, H), (255, 255, 255)), .7 - .35 * i)
        if cap and i >= cap_from:
            k = i - cap_from; s = [1.6, 1.2, .97, 1.0][k] if k < 4 else 1.0
            ci = cap.resize((int(cap.width * s * .62), int(cap.height * s * .62)), Image.NEAREST)
            band = Image.new('RGBA', (W, ci.height + 40), (0, 0, 0, 150)); im.paste(band, (0, H - ci.height - 110), band)
            im.paste(ci, ((W - ci.width) // 2, H - ci.height - 90), ci)
        emit(im)

def fix_results(im):
    # the fake clock left 'Invalid Date' in the results header; paint the line over
    d = ImageDraw.Draw(im); c = im.getpixel((132, 62)); d.rectangle([140, 42, 980, 86], fill=c)
    d.text((152, 52), 'PRACTICE ROUND', font=ImageFont.truetype(PIX, 20), fill=GOLD)

def main():
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
    card([("THINK YOU'RE", 96, WHITE)], 15)
    card([("SMART ENOUGH", 96, WHITE)], 15)
    card([("TO MAKE IT AS AN", 64, WHITE), ("NFL QUARTERBACK?", 104, GOLD)], 34)
    footage('01_routes', 12, 90, [("REAL NFL PLAYS.", 64, WHITE), ("REAL TRACKING DATA.", 64, GOLD)], cap_from=6)
    card([("MEMORIZE THE ROUTES.", 80, WHITE)], 17)
    nd = len(os.listdir(os.path.join(FR, '02_drop')))
    footage('02_drop', 0, nd, [("AT THE SNAP", 64, WHITE), ("YOU'RE THE QB.", 64, GOLD)], cap_from=4)
    footage('03_freeze', 0, 24, [("THE PRO THREW HERE.", 64, WHITE), ("YOUR CALL.", 64, GOLD)], cap_from=1)
    card([("3 SECONDS.", 120, GOLD)], 16)
    footage('04_catch', 18, 48)
    footage('04_catch', 60, 176, flash_in=False)
    footage('05_banner', 2, 62, flash_in=False)
    card([("BEAT THE PRO'S", 80, WHITE), ("REAL DECISION.", 80, GREEN)], 26)
    footage('06_review', 8, 58)
    footage('07_results', 0, 46, fix=fix_results)
    card([("OR LOSE YOUR JOB", 80, WHITE), ("TO TOM BRADY.", 80, GOLD)], 28)
    footage('08_bledsoe', 0, 66)
    card([("POCKET PASSER", 120, GOLD), ("THINK YOU'RE SMART ENOUGH?", 44, WHITE), ("PLAY FREE  POCKETPASSER.ONRENDER.COM", 32, (169, 184, 175))], 80)
    dur = n / FPS; fade = max(0, dur - 1.6)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(OUT, '%05d.png'), '-i', MUSIC,
                    '-filter_complex', f'[1:a]atrim=0:{dur:.2f},afade=t=in:d=0.3,afade=t=out:st={fade:.2f}:d=1.6[a]',
                    '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', DEST], check=True)
    print(f'{n} frames, {dur:.1f} s ->', DEST)

if __name__ == '__main__':
    main()
