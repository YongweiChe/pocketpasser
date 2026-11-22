# Beat the Pro — QB Cam

A first-person browser QB game. You memorize a play, take the snap, and throw (early, or at the freeze when the real QB released it). Your decision is scored in EPA against the pro's actual throw. The game has a Daily 6 (the same 6 plays for everyone each day, with a leaderboard), practice rounds, and a tutorial.

## Files
| File | What it is |
|---|---|
| `fp2_src.html` | **3D game source** (three.js 0.160 via import map from jsdelivr). Edit this. |
| `index.html` | 2D prototype. It also **owns the shared model**: the hand-made drill plays, `pos()`, `evaluate()` (catch/INT/EPA model), `reactOf()`, `heatmap()`, `makePlan()`/`step()` (throw outcome + post-throw motion). |
| `build.py` | Splices the model from `index.html` into the `/*MODEL*/` and `/*PLAN*/` placeholders of `fp2_src.html`. Writes `fp2.html` (fetches `real_plays.json`, needs a web server) and `beat-the-pro-qb-cam.html` (standalone, data inlined, works from file://). **Run after every edit.** |
| `real_plays.json` | 15 real NFL passing plays (NGS highlight tracking, 5 Hz, QB-relative coords). |
| `data/convert.py` | Builds `real_plays.json` from `data/raw/*.tsv` (NFL Next Gen Stats highlight clips from github.com/asonty/ngs_highlights). Per defender it stores top speed (max of tracked speed and the position norm) and a per-frame facing angle (`o`). It auto-fixes clips whose orientation is rotated 90° (the 2017 Keenum clip). |
| `data/real.js` | Node version of `realToPlay()` for model tests. |
| `tests/` | Playwright end-to-end scripts: tutorial flow, forced outcomes/cutscenes, art-style sprite export. |

## Run / test
```bash
python3 build.py
open beat-the-pro-qb-cam.html            # or: python3 -m http.server, then open fp2.html
npm i three@0.160.0 playwright && npx playwright install chromium
python3 tests/e2e_tutorial.py            # prints ['results', 'Play today’s 6', 'Tutorial complete'] then [] (no errors)
```
Debug hooks on `window`: `__S` (state), `__PLAYS`, `__load(i)`, `__force(x,y,type,kind,sub,yac)` (force an outcome), `__showResults()`, `__setArt(style)`, `__atlas(style,side,num)`.

## Model in one paragraph
Throw = target spot + type (fastball: 0.05 + d/23 s; touch: 0.15 + d/18.5 s; calibrated to real air times). The receiver who can reach the spot is found with a route-gap model and a "read it, brake, come back" redirect model; the smaller gap wins, and a reversal means "thrown behind". After the release, defenders keep their real tracking for a reaction delay. On real plays that delay comes from facing (0.22 s facing the QB to 0.62 s back turned); on drills it's fixed. Then they close at 85% of their sprint speed. Odds: pC ≈ 0.94 − 0.2·gap (−0.06 if behind) × (1 − 0.8·contest), INT rises with defender closeness, plus tip risk from underneath defenders in the ball's low segments. EPA uses a toy EP formula (not nflfastR). A drop is the leftover incompletion when the ball was reachable and no tip or breakup won the roll.

## Decisions the user has made (don't undo without asking)
- **Aiming = click a spot on the field (floor).** The user tried and rejected: chest-height aim, a dotted arc/side-view inset, route-snap with a ghost receiver, and trajectory hoops. Keep it simple.
- **Animations:** keep the current ones. A slapstick pass was tried and reverted.
- **Art style:** the cardboard cutout is the default. "Clean flat", "Painted" and "Retro pixel" are selectable on the start screen (V cycles). They share one 8-frame sprite atlas (front/back × stand/runA/runB/up), so the animation is identical across styles. The user wants more polished character styles; this is the open thread.
- No photos of real people (QBs) in the game.
- Routes toggle exists for practice/tutorial; it's forced off in Today's 6 so the leaderboard is fair.
- Look controls: 1/2/3 snap the view left/middle/right; arrow keys free-look during the play; the view locks at the freeze.
- Throwing early is allowed after a 0.6 s drop.
- A receiver who has settled (curl/hitch) turns to the QB, bounces on his toes and waves; both hands go up when the ball is coming to him.

## Leaderboard
It uses the claude.ai Artifacts db capability (`claude.use('db')`, Firestore-like API) and only works on the published artifact. The public "Beat the Pro: Daily 6" artifact is a few versions behind this code. Publishing there needs the user's approval. Outside a claude.ai artifact the board shows "isn't available"; a real backend would be needed elsewhere (e.g. for friends' matchmaking rooms).

## Backlog (also in the user's "Beat the Pro — Feature Backlog" doc)
- [ ] Import the full Big Data Bowl dataset (Kaggle CSVs) → hundreds of plays, real season-long top speeds.
- [ ] Learned completion-probability model trained on BDB to replace the hand-tuned odds.
- [ ] Versus mode: play only one real QB's snaps and try to beat him.
- [ ] Versus friends: shared room, same plays, N tries, head-to-head (needs a backend).
- [ ] Real recorded voice lines (cadence, "set, hut", crowd) — waiting on audio files.
- [ ] More polished character art (current exploration).
