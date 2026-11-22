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
src = open(p('fp2_src.html')).read()

ms = ix.index("const W=53.33")
me = ix.index('  return{cells,best};\n}', ms) + len('  return{cells,best};\n}')

st = ix.index('/* ---------- throw plan + animation ---------- */')
endm = "first down':'');\n}"
e = ix.index(endm, st) + len(endm)
plan = ix[st:e]
a = plan.index('function ballState(){')
b = plan.index('/* ---------- result panel ---------- */\n') + len('/* ---------- result panel ---------- */\n')
plan = plan[:a] + plan[b:]

out = src.replace('/*MODEL*/', ix[ms:me], 1).replace('/*PLAN*/', plan, 1)
open(p('fp2.html'), 'w').write(out)

data = open(p('real_plays.json')).read()
standalone = out.replace("fetch('real_plays.json').then(r=>r.json()).then(R=>{",
                         "const REAL_DATA=" + data + ";Promise.resolve(REAL_DATA).then(R=>{", 1)
open(p('beat-the-pro-qb-cam.html'), 'w').write(standalone)
print('built fp2.html and beat-the-pro-qb-cam.html')
