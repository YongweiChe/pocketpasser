"""Build the game.

fp2_src.html is the 3D game source. It has two placeholders that get filled from index.html (the 2D game,
which owns the shared play data + throw/EPA model):
  /*MODEL*/  <- index.html from `const W=53.33` through the end of heatmap()
  /*PLAN*/   <- index.html's "throw plan + animation" section (makePlan, sackPlan, awayPlan, startThrow, step,
                tipPoint, describe), minus ballState() which the 3D game replaces.
Outputs:
  fp2.html                  -- loads real_plays.json with fetch (needs a local web server)
  beat-the-pro-qb-cam.html  -- standalone single file with the real-play data inlined (works from file://)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
p = lambda name: os.path.join(HERE, name)

ix = open(p('index.html')).read()
import base64
src = open(p('fp2_src.html')).read()
# the pixel football, inlined where the page shows it (works from file:// and the local server too)
if os.path.exists(p('site/favicon.svg')):
    src = src.replace('src="__FOOTBALL__"', 'src="data:image/svg+xml;base64,' + base64.b64encode(open(p('site/favicon.svg'), 'rb').read()).decode() + '"')

ms = ix.index("const W=53.33")
me = ix.index('  return{cells,best};\n}', ms) + len('  return{cells,best};\n}')

st = ix.index('/* ---------- throw plan + animation ---------- */')
endm = "first down':'');\n}"
e = ix.index(endm, st) + len(endm)
plan = ix[st:e]
a = plan.index('function ballState(){')
b = plan.index('/* ---------- result panel ---------- */\n') + len('/* ---------- result panel ---------- */\n')
plan = plan[:a] + plan[b:]

# recorded cadences (optional, gitignored): audio/cadence/manifest.json lists clips + where "hut" lands in each.
# fp2.html fetches the files; the standalone build embeds them as data: URIs so it still works from file://
import json, base64
man_path = p('audio/cadence/manifest.json')
cad = json.load(open(man_path)) if os.path.exists(man_path) else []
def cad_js(embed):
    items = []
    for c in cad:
        src = c['src']
        if embed:
            src = 'data:audio/mpeg;base64,' + base64.b64encode(open(p(c['src']), 'rb').read()).decode()
        items.append({'src': src, 'hut': c['hut']})
    return 'const CADENCE_FILES=' + json.dumps(items) + ';'

# announcer soundbites: announcer_lines.json holds every line (ID -> text); audio/announcer/<ID>.<ext> overrides the robot voice
lines = {k: v for k, v in json.load(open(p('announcer_lines.json'))).items() if not k.startswith('_')} if os.path.exists(p('announcer_lines.json')) else {}
ann_files = {}
ann_dir = p('audio/announcer')
if os.path.isdir(ann_dir):
    for f in sorted(os.listdir(ann_dir)):
        stem, ext = os.path.splitext(f)
        if stem in lines and ext.lower() in ('.mp3', '.wav', '.ogg', '.m4a'):
            ann_files[stem] = 'audio/announcer/' + f
missing = [k for k in lines if k not in ann_files]
MIME = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.m4a': 'audio/mp4'}
def ann_js(embed):
    files = {k: ('data:' + MIME[os.path.splitext(v)[1].lower()] + ';base64,' + base64.b64encode(open(p(v), 'rb').read()).decode()) if embed else v
             for k, v in ann_files.items()}
    return 'const ANN_LINES=' + json.dumps(lines) + ';const ANN_FILES=' + json.dumps(files) + ';'

out = src.replace('/*MODEL*/', ix[ms:me], 1).replace('/*PLAN*/', plan, 1)
# home-page music: audio/music/home.mp3 if present (otherwise the game's synthesized brass theme)
music = 'audio/music/home.mp3' if os.path.exists(p('audio/music/home.mp3')) else None
def music_js(embed):
    if not music: return 'const MUSIC_FILE=null;'
    return 'const MUSIC_FILE=' + json.dumps('data:audio/mpeg;base64,' + base64.b64encode(open(p(music), 'rb').read()).decode() if embed else music) + ';'
out_embed = out.replace('/*CADENCE*/', cad_js(True), 1).replace('/*ANNOUNCER*/', ann_js(True), 1).replace('/*MUSIC*/', music_js(True), 1)
out = out.replace('/*CADENCE*/', cad_js(False), 1).replace('/*ANNOUNCER*/', ann_js(False), 1).replace('/*MUSIC*/', music_js(False), 1)
open(p('fp2.html'), 'w').write(out)

# public/: what the website serves (Render publishes this folder). Only shareable assets: the game, the highlight plays,
# the announcer clips and the home music. Never the Big Data Bowl plays or the broadcast cadence clips.
import shutil
pub = p('public')
shutil.rmtree(pub, ignore_errors=True)
os.makedirs(os.path.join(pub, 'audio', 'announcer'))
public_page = src.replace('/*MODEL*/', ix[ms:me], 1).replace('/*PLAN*/', plan, 1)
public_page = public_page.replace('/*CADENCE*/', 'const CADENCE_FILES=[];', 1).replace('/*ANNOUNCER*/', ann_js(False), 1).replace('/*MUSIC*/', music_js(False), 1)
public_page = public_page.replace("fetch('data/bdb_plays/index.json')", "Promise.resolve({ok:false})", 1)   # the site never has the season plays: don't ask (a 404 on every visit)
open(os.path.join(pub, 'index.html'), 'w').write(public_page)
shutil.copy(p('real_plays.json'), pub)
# auth.html: the sign-in popup's landing page, with the same Supabase project as the game
import re as _re
_m = _re.search(r"const SUPA=(\{url:'[^']*',key:'[^']*'\})", src)
_auth = open(p('auth_src.html')).read().replace('/*SUPA*/', _m.group(1) if _m else "{url:'',key:''}", 1)
open(p('auth.html'), 'w').write(_auth); open(os.path.join(pub, 'auth.html'), 'w').write(_auth)
for f in os.listdir(p('site')): shutil.copy(p(os.path.join('site', f)), pub)   # favicon, touch icon, link-preview image
shutil.copy(p('site/favicon-32.png'), os.path.join(pub, 'favicon.ico'))   # browsers and bots still ask for /favicon.ico
for v in ann_files.values(): shutil.copy(p(v), os.path.join(pub, v))
if music: os.makedirs(os.path.join(pub, 'audio', 'music'), exist_ok=True); shutil.copy(p(music), os.path.join(pub, music))

data = open(p('real_plays.json')).read()
standalone = out_embed.replace("fetch('real_plays.json').then(r=>r.json()).then(R=>{",
                         "const REAL_DATA=" + data + ";Promise.resolve(REAL_DATA).then(R=>{", 1)
open(p('beat-the-pro-qb-cam.html'), 'w').write(standalone)
print('built fp2.html and beat-the-pro-qb-cam.html' + (f' ({len(cad)} recorded cadences)' if cad else '') + (', home music: ' + music if music else ''))
if lines:
    # the to-do list for voice generation: every line that still has no recording (ID = the filename to save it as)
    import csv
    os.makedirs(ann_dir, exist_ok=True)
    with open(os.path.join(ann_dir, 'todo.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['filename', 'text'])
        for k in missing: w.writerow([k + '.mp3', lines[k]])
    print(f'announcer: {len(ann_files)} of {len(lines)} lines recorded' + (f'; the rest stay silent until recorded (see audio/announcer/todo.csv)' if missing else ''))
