"""Fit the game's expected-points table from nflverse expected_points (via Big Data Bowl play files) and write it into index.html.

EP(down, distance, yards-to-goal) is the average nflverse EP of real plays in that situation (all clocks and scores),
smoothed with a Gaussian kernel over yard line and log-distance within each down; the window widens where data is thin.
Validation: fit on 2023-24, score on held-out 2025 plays, compared with the old hand-written formula.
The table is derived statistics (no tracking or play-level data), so it can ship in the public game.
Usage: python3 data/fit_ep.py            (writes the table between /*EP_TABLE*/ markers in index.html)
"""
import json, os, re, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COLS = ['game_id', 'play_id', 'down', 'yards_to_go', 'possession_team', 'yardline_side', 'yardline_number', 'expected_points']
DMAX = 20


def load():
    parts = []
    a = os.path.join(HERE, 'bdb', 'player_play.csv')
    b = os.path.join(HERE, 'bdb2026', 'supplementary_data.csv')
    if os.path.exists(a): parts.append(pd.read_csv(a, usecols=COLS, low_memory=False).drop_duplicates(['game_id', 'play_id']))
    if os.path.exists(b): parts.append(pd.read_csv(b, usecols=COLS, low_memory=False))
    if not parts: sys.exit('No Big Data Bowl files found in data/bdb or data/bdb2026.')
    x = pd.concat(parts).drop_duplicates(['game_id', 'play_id'])
    x = x[x.down.between(1, 4) & x.expected_points.notna() & x.yards_to_go.between(1, 99)].copy()
    side = x.yardline_side.fillna('')
    x['ytg'] = np.where(x.yardline_number == 50, 50, np.where(side == x.possession_team, 100 - x.yardline_number, x.yardline_number))
    x = x[x.ytg.between(1, 99)]
    x['dist'] = np.minimum(x.yards_to_go, x.ytg)
    # season: NFL game ids start with the calendar date; Jan/Feb games belong to the previous season
    gid = x.game_id.astype(str)
    x['season'] = gid.str[:4].astype(int) - (gid.str[4:6].astype(int) <= 2)
    return x


def fit(x):
    """table[down-1][dist-1][ytg-1]"""
    T = np.zeros((4, DMAX, 99))
    ys, ds = np.arange(1, 100), np.arange(1, DMAX + 1)
    for dn in range(1, 5):
        s = x[x.down == dn]
        py, pd_, pe = s.ytg.values.astype(float), np.log(np.minimum(s.dist.values, DMAX).astype(float)), s.expected_points.values
        for di, d in enumerate(ds):
            for yi, y in enumerate(ys):
                dd = min(d, y)   # distance can't exceed yards to goal (goal to go)
                sy, sd = 2.5, 0.18
                for _ in range(6):   # widen the window until there is enough data behind the cell
                    w = np.exp(-((py - y) / sy) ** 2 / 2 - ((pd_ - np.log(dd)) / sd) ** 2 / 2)
                    if w.sum() >= 40: break
                    sy, sd = sy * 1.6, sd * 1.5
                T[dn - 1, di, yi] = (w * pe).sum() / max(w.sum(), 1e-9)
    return T


def lookup(T, down, dist, ytg):
    return T[down - 1, np.clip(np.minimum(dist, ytg), 1, DMAX) - 1, np.clip(ytg, 1, 99) - 1]


def toy(down, dist, ytg):   # the formula the game used before
    DADJ = {1: 0, 2: -.45, 3: -1.05, 4: -1.9}; DK = {1: .03, 2: .05, 3: .08, 4: .1}
    return 6.3 - .071 * ytg + np.vectorize(DADJ.get)(down) - np.vectorize(DK.get)(down) * (np.minimum(dist, ytg) - 10)


def main():
    x = load()
    print(f'{len(x):,} plays with nflverse EP, seasons {sorted(x.season.unique())}')
    tr, te = x[x.season <= 2024], x[x.season >= 2025]
    T = fit(tr)
    for name, pred in [('fitted table', lookup(T, te.down.values, te.dist.values.astype(int), te.ytg.values.astype(int))),
                       ('old formula', toy(te.down.values, te.dist.values, te.ytg.values))]:
        err = pred - te.expected_points.values
        print(f'  held-out 2025 ({len(te):,} plays) {name:<12}: RMSE {np.sqrt((err ** 2).mean()):.3f}  mean error {err.mean():+.3f}')
    T = fit(x)   # final table uses every season
    ints = (np.round(T * 100)).astype(int).ravel().tolist()
    block = '/*EP_TABLE*/const EPT=' + json.dumps(ints, separators=(',', ':')) + ';/*EP_TABLE_END*/'
    p = os.path.join(ROOT, 'index.html'); s = open(p).read()
    if '/*EP_TABLE*/' not in s: sys.exit('index.html has no /*EP_TABLE*/ marker')
    s = re.sub(r'/\*EP_TABLE\*/.*?/\*EP_TABLE_END\*/', lambda m: block, s, flags=re.S)
    open(p, 'w').write(s)
    print('wrote the table into index.html;', 'sample 1st & 10:', {y: round(float(T[0, 9, y - 1]), 2) for y in (99, 80, 75, 50, 25, 10)},
          '| 3rd & 2 at midfield', round(float(T[2, 1, 49]), 2), '| 4th & 1 at the 1', round(float(T[3, 0, 0]), 2))


if __name__ == '__main__':
    main()
