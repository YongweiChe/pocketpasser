"""Trailer v2 edit: one continuous take (no hard cuts), titles fading over the footage, the replay sped up (not cut) so
the catch runs straight into the win banner, a fade to the end card. Usage: python3 tools/trailer/compose2.py OUT.mp4 [CATCH]
CATCH = frame in s8_catch where the ball is caught (normal speed until then, faster after)."""
import os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); PORTRAIT = '--portrait' in sys.argv; sys.argv = [a for a in sys.argv if a != '--portrait']
FR, OUT = os.path.join(HERE, 'frames2v' if PORTRAIT else 'frames2'), os.path.join(HERE, 'out2v' if PORTRAIT else 'out2')
W, H, FPS = (1080, 1920, 30) if PORTRAIT else (1920, 1080, 30)
TS = .62 if PORTRAIT else 1.0   # title scale: the vertical frame is narrower
PIX = os.path.join(HERE, 'font', 'PressStart2P.ttf')
GOLD, WHITE, GREEN, MUTE = (245, 197, 24), (255, 255, 255), (74, 222, 128), (169, 184, 175)
MUSIC = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'audio', 'music', 'home.mp3')
DEST = sys.argv[1]; CATCH = int(sys.argv[2]) if len(sys.argv) > 2 else 120
n = 0

def emit(im):
    global n
    im.convert('RGB').save(os.path.join(OUT, '%05d.png' % n)); n += 1

def text_img(lines, gap=30):
    fonts = [ImageFont.truetype(PIX, max(12, int(s * TS))) for _, s, _ in lines]; bb = [f.getbbox(t) for (t, _, _), f in zip(lines, fonts)]
    w = max(b[2] - b[0] for b in bb) + 40; h = sum(b[3] - b[1] for b in bb) + gap * (len(lines) - 1) + 40
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); y = 12
    for (t, s, c), f, b in zip(lines, fonts, bb):
        x = (w - (b[2] - b[0])) // 2 - b[0]; sh = max(4, s // 10)
        d.text((x + sh, y - b[1] + sh), t, font=f, fill=(0, 0, 0, 255)); d.text((x, y - b[1]), t, font=f, fill=c + (255,)); y += b[3] - b[1] + gap
    return im

def frames_of(seg, a=0, b=None, step=1):
    fs = sorted(os.listdir(os.path.join(FR, seg)))[a:b:step]
    return [os.path.join(FR, seg, f) for f in fs]

def load(path): return Image.open(path).convert('RGB').resize((W, H), Image.LANCZOS)

def with_alpha(im, a):
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im

def play(paths, title=None, where='low', t_in=0, t_out=None, fade=10):
    """footage with an optional title that fades in at t_in and out at t_out (frame indices within this shot)"""
    t = text_img(title) if title else None; t_out = len(paths) if t_out is None else t_out
    for i, pth in enumerate(paths):
        im = load(pth)
        if t and t_in <= i < t_out:
            a = min(1, (i - t_in + 1) / fade, (t_out - i) / fade)
            if where == 'mid':   # centred title over a soft dark wash
                wash = Image.new('RGBA', (W, H), (4, 8, 14, int(110 * a))); im.paste(wash, (0, 0), wash)
                ti = with_alpha(t, a); im.paste(ti, ((W - t.width) // 2, (H - t.height) // 2 - 40), ti)
            elif where == 'right':  # a panel over the stands on the right (keeps the field and the game's panel clear)
                ts = t.resize((int(t.width * .5), int(t.height * .5)), Image.NEAREST)
                x, y = W - ts.width - 70, (H - ts.height) // 2
                band = Image.new('RGBA', (ts.width + 40, ts.height + 30), (0, 0, 0, int(160 * a))); im.paste(band, (x - 20, y - 15), band)
                ti = with_alpha(ts, a); im.paste(ti, (x, y), ti)
            else:                # lower third on a band
                k = .9 if PORTRAIT else .62; lift = 420 if PORTRAIT else 120
                ts = t.resize((int(t.width * k), int(t.height * k)), Image.NEAREST)
                band = Image.new('RGBA', (W, ts.height + 44), (0, 0, 0, int(150 * a))); im.paste(band, (0, H - ts.height - lift), band)
                ti = with_alpha(ts, a); im.paste(ti, ((W - ts.width) // 2, H - ts.height - lift + 22), ti)
        emit(im)

def main():
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
    push = frames_of('s12_push')                                                     # 1-2: 0-7 s
    play(push[:120], [("THINK YOU'RE", 72, WHITE), ("SMART ENOUGH", 72, WHITE)], 'mid', 12, 118)
    play(push[120:], [("TO MAKE IT AS AN", 56, WHITE), ("NFL QUARTERBACK?", 84, GOLD)], 'mid', 2, 88)
    play(frames_of('s3_routes'), [("REAL NFL PLAYS.", 64, WHITE), ("REAL TRACKING DATA.", 64, GOLD)], 'low', 30, 118)   # 3
    play(frames_of('s4_memorize'), [("MEMORIZE THE ROUTES.", 64, WHITE)], 'low', 6, 116)                                # 4
    drop = frames_of('s56_drop')                                                     # 5-6: snap, drop into the QB's eyes
    play(drop, [("DROP INTO THE", 64, WHITE), ("QUARTERBACK'S SLOT.", 64, GOLD)], 'low', 0, 62)
    play(frames_of('s7_freeze'), [("THE PRO THREW HERE.", 64, WHITE), ("YOUR CALL.", 64, GOLD)], 'low', 6, 88)          # 7
    catch = frames_of('s8_catch')                                                    # 8: normal speed to the catch, then 3x (no cut)
    play(catch[:CATCH] + catch[CATCH::3])
    play(frames_of('s9_banner'))                                                     # 9: the win banner, straight on from the catch
    rev = frames_of('s10_review')                                                    # 10: the replay view
    play(rev[:90], [("BEAT THE PRO'S", 64, WHITE), ("REAL DECISION.", 64, GREEN)], 'low' if PORTRAIT else 'right', 8, 90)
    # 11: fade from the replay view to the field with the end card
    last = load(rev[89]); field = load(frames_of('s3_routes')[60]).filter(ImageFilter.GaussianBlur(6))
    end = text_img([("POCKET PASSER", 104, GOLD), ("THINK YOU'RE SMART ENOUGH?", 40, WHITE), ("POCKETPASSER.ONRENDER.COM", 30, MUTE)], gap=36)
    for i in range(105):
        k = min(1, i / 24); im = Image.blend(last, field, k)
        wash = Image.new('RGBA', (W, H), (4, 8, 14, int(150 * k))); im.paste(wash, (0, 0), wash)
        a = min(1, max(0, (i - 14) / 14)); ti = with_alpha(end, a); im.paste(ti, ((W - end.width) // 2, (H - end.height) // 2), ti)
        if i > 90: im = Image.blend(im, Image.new('RGB', (W, H), (0, 0, 0)), (i - 90) / 15)
        emit(im)
    dur = n / FPS
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(OUT, '%05d.png'), '-i', MUSIC,
                    '-filter_complex', f'[1:a]atrim=0:{dur:.2f},afade=t=in:d=1.2,afade=t=out:st={dur - 2.2:.2f}:d=2.2[a]',
                    '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', DEST], check=True)
    print(f'{n} frames, {dur:.1f} s ->', DEST)

if __name__ == '__main__':
    main()
