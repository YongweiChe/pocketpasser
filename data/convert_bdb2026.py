"""Convert Big Data Bowl 2026 tracking (2023 season, ~14k pass plays) into the game's real-play format.

Input:  data/bdb2026/ (gitignored): input_2023_wNN.csv (every player from the snap to the release, 10 Hz),
        output_2023_wNN.csv (target + nearby defenders while the ball is in the air), supplementary_data.csv.
Output: data/bdb_plays/<key>.json, one play per file, plus data/bdb_plays/index.json (all gitignored).
        LOCAL USE ONLY: NFL tracking under Big Data Bowl terms. Never bundle these into a published build.

Gaps in this dataset and how they are filled (all marked in the play so the game can tell):
  - no offensive/defensive linemen: 5 blockers + 4 rushers are generated around the real snap spot
  - after the throw only the target and a few defenders are tracked: everyone else continues at their last velocity
  - no jersey numbers: players get synthetic numbers for ids, and position labels (WR1, TE, RB...) for display
  - no ball tracking: the throw spot is the recorded landing spot, air time = the number of in-air frames
Usage: python3 data/convert_bdb2026.py [--weeks 1,2,...]
"""
import argparse, glob, json, math, os, re, statistics, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'bdb2026')
OUT = os.path.join(HERE, 'bdb_plays')
W = 53.33
TEAMS = {'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens', 'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers',
         'CHI': 'Chicago Bears', 'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys', 'DEN': 'Denver Broncos',
         'DET': 'Detroit Lions', 'GB': 'Green Bay Packers', 'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars',
         'KC': 'Kansas City Chiefs', 'LA': 'Los Angeles Rams', 'LAC': 'Los Angeles Chargers', 'LV': 'Las Vegas Raiders', 'MIA': 'Miami Dolphins',
         'MIN': 'Minnesota Vikings', 'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants', 'NYJ': 'New York Jets',
         'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers', 'SEA': 'Seattle Seahawks', 'SF': 'San Francisco 49ers',
         'TB': 'Tampa Bay Buccaneers', 'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders'}
DB = ('CB', 'DB', 'S', 'SS', 'FS')
STEP = 2            # keep every 2nd 10 Hz frame -> 5 Hz like the highlight plays
TAIL = 1.2          # seconds of motion kept after the ball lands


class Skip(Exception):
    pass


def r2(v):
    return round(float(v), 2)


def convert_play(g, play_id, df, outdf, sp):
    df = df.sort_values('frame_id')
    if sp is None:
        raise Skip('no play info')
    if str(sp['pass_result']) not in ('C', 'I', 'IN') or str(sp['play_nullified_by_penalty']) == 'Y':
        raise Skip('not a usable pass')
    down = int(sp['down']) if not pd.isna(sp['down']) else 0
    if down not in (1, 2, 3, 4):
        raise Skip('no down')
    roles = df.drop_duplicates('nfl_id').set_index('nfl_id')
    if (roles.player_role == 'Passer').sum() != 1 or (roles.player_role == 'Targeted Receiver').sum() != 1:
        raise Skip('needs one passer and one target')
    nin = df.frame_id.nunique()
    T = (nin - 1) / 10
    nout = int(df.num_frames_output.iloc[0])
    air = nout / 10
    if not (0.8 <= T <= 8 and 0 < air <= 4.5):
        raise Skip('odd timing')
    d = 1 if df.play_direction.iloc[0] == 'right' else -1
    losX = float(df.absolute_yardline_number.iloc[0])
    tx = lambda x, y: ((W - y) if d > 0 else y, (x - losX) * d)
    # orientation sanity (older NGS clips were rotated 90 deg): compare facing with direction for fast movers
    fast = df[df.s > 4.5]
    off_o = round(statistics.median(((fast.o - fast.dir + 180) % 360 - 180).tolist()) / 90) * 90 if len(fast) > 5 else 0
    t_end = T + air + TAIL
    times = [k * 0.1 * STEP for k in range(int(t_end / (0.1 * STEP)) + 1)]

    def track(pid):
        a = df[df.nfl_id == pid].sort_values('frame_id')
        pts = {(int(f) - 1) / 10: tx(x, y) for f, x, y in zip(a.frame_id, a.x, a.y)}
        o_last = a.o.iloc[-1]
        b = outdf[outdf.nfl_id == pid].sort_values('frame_id') if outdf is not None else None
        if b is not None and len(b):
            for f, x, y in zip(b.frame_id, b.x, b.y):
                pts[T + int(f) / 10] = tx(x, y)
        ks = sorted(pts)
        # velocity from the last 0.2 s actually tracked, then continue at that velocity (capped at 11 yd/s)
        k1, k0 = ks[-1], ks[max(0, len(ks) - 3)]
        dt = max(1e-6, k1 - k0)
        vx, vy = (pts[k1][0] - pts[k0][0]) / dt, (pts[k1][1] - pts[k0][1]) / dt
        sp_ = math.hypot(vx, vy)
        if sp_ > 11:
            vx, vy = vx * 11 / sp_, vy * 11 / sp_
        f, ori = [], []
        for t in times:
            if t <= k1 + 1e-6:
                # nearest tracked sample at or before t (data is 10 Hz, samples are 5 Hz, so this is exact)
                kk = min(ks, key=lambda k: abs(k - t))
                x, y = pts[kk]
            else:
                x, y = pts[k1][0] + vx * (t - k1), pts[k1][1] + vy * (t - k1)
            f += [r2(t), r2(x), r2(y)]
            # facing angle in game coords (deg, atan2(dy,dx)); after the input frames keep the last one
            row = a[a.frame_id <= 1 + round(t * 10)]
            o = (row.o.iloc[-1] if len(row) else o_last) - off_o
            so, co = math.sin(math.radians(o)), math.cos(math.radians(o))
            gx, gy = (-co, so) if d > 0 else (co, -so)
            ori.append(round(math.degrees(math.atan2(gy, gx))))
        return f, ori, a

    qb_id = roles.index[roles.player_role == 'Passer'][0]
    qf, _, qa = track(qb_id)
    qb = {'num': None, 'name': str(roles.loc[qb_id, 'player_name']), 'pos': 'QB', 'f': qf}
    qx0 = qf[1]
    off, de = [], []
    used = set()

    def num_for(pos, side):
        ranges = {'WR': list(range(10, 20)) + list(range(80, 90)), 'TE': list(range(80, 90)) + list(range(40, 50)), 'RB': list(range(20, 40)),
                  'FB': list(range(40, 50)) + list(range(20, 40)), 'CB': list(range(20, 40)), 'FS': list(range(20, 50)), 'SS': list(range(20, 50)),
                  'S': list(range(20, 50)), 'ILB': list(range(50, 60)), 'MLB': list(range(50, 60)), 'OLB': list(range(40, 60)),
                  'LB': list(range(50, 60)), 'DE': list(range(90, 100)), 'DT': list(range(90, 100)), 'NT': list(range(90, 100))}
        for n in ranges.get(pos, list(range(1, 100))) + list(range(1, 100)):
            if (side, n) not in used:
                used.add((side, n))
                return n
    for pid, r in roles.iterrows():
        if pid == qb_id:
            continue
        pos = str(r.player_position)
        f, ori, a = track(pid)
        top = float(a.s.max())
        if r.player_side == 'Offense':
            p = {'num': num_for(pos, 'o'), 'name': str(r.player_name), 'pos': pos, 'f': f, 'elig': pos in ('WR', 'TE', 'RB', 'FB', 'HB'),
                 'speed': round(min(9.5, max(6.2, top)), 2)}
            if r.player_role == 'Targeted Receiver':
                p['target'] = True
            off.append(p)
        else:
            yT = None
            for i in range(0, len(f), 3):
                if f[i] <= T + .05:
                    yT = f[i + 2]
            base = 8 if pos in DB else 7 if 'LB' in pos else 6.2
            de.append({'num': num_for(pos, 'd'), 'name': str(r.player_name), 'pos': pos, 'f': f, 'o': ori,
                       'rush': pos in ('DE', 'DT', 'NT', 'DL') or (yT is not None and yT < -.5),
                       'sprint': round(min(9.8, max(base, top)), 2), 'react': .4 if pos in DB else .35})
    tgt = next((p for p in off if p.get('target')), None)
    if tgt is None or not tgt['elig'] or sum(p['elig'] for p in off) < 2:
        raise Skip('target is not a WR/TE/RB')
    # generated line: 5 blockers sinking into a pocket, 4 rushers pushing up the field (they never cover anyone)
    for k, (pos, dx) in enumerate(zip(('T', 'G', 'C', 'G', 'T'), (-4.4, -2.2, 0, 2.2, 4.4))):
        f = []
        for t in times:
            f += [r2(t), r2(qx0 + dx * (1 + .04 * min(t, 2.5))), r2(-.8 - min(1.7, t * .85))]
        off.append({'num': 60 + k * 3 + (k > 2) * 5, 'name': 'Offensive lineman', 'pos': pos, 'f': f, 'elig': False, 'speed': 6, 'gen': True})
    for k, (pos, dx) in enumerate(zip(('DE', 'DT', 'DT', 'DE'), (-5.6, -1.4, 1.4, 5.6))):
        f = []
        for t in times:
            f += [r2(t), r2(qx0 + dx * (1 - .06 * min(t, 2.5))), r2(.9 - min(2.2, t * 1.0))]
        de.append({'num': 90 + k, 'name': 'Defensive lineman', 'pos': pos, 'f': f, 'o': [-90] * len(times), 'rush': True, 'sprint': 6.2,
                   'react': .35, 'gen': True})
    # display labels: receivers left to right (WR1, WR2...), one-of-a-kind positions keep their name
    rec = sorted([p for p in off if p['elig']], key=lambda p: p['f'][1])
    cnt = {}
    for p in rec:
        cnt[p['pos']] = cnt.get(p['pos'], 0) + 1
    seen = {}
    for p in rec:
        seen[p['pos']] = seen.get(p['pos'], 0) + 1
        p['lab'] = p['pos'] + (str(seen[p['pos']]) if cnt[p['pos']] > 1 else '')
    # the throw: recorded landing spot, air time from the in-air frames; fastball vs touch from the game's flight model
    spot = tx(float(df.ball_land_x.iloc[0]), float(df.ball_land_y.iloc[0]))
    if not (-5 <= spot[0] <= W + 5 and -15 <= spot[1] <= 70):
        raise Skip('landing spot off the field')
    qT = next((qf[i + 1], qf[i + 2]) for i in range(len(qf) - 3, -1, -3) if qf[i] <= T + .05)
    dd = math.hypot(spot[0] - qT[0], spot[1] - qT[1])
    typ = 'fast' if abs((.05 + dd / 23) - air) <= abs((.15 + dd / 18.5) - air) else 'touch'
    kind = {'C': 'complete', 'I': 'incomplete', 'IN': 'int'}[str(sp['pass_result'])]
    gain = int(sp['yards_gained']) if not pd.isna(sp['yards_gained']) else 0
    yac = max(0, gain - round(spot[1])) if kind == 'complete' else 0
    ytg = round(110 - losX) if d > 0 else round(losX - 10)
    posT, defT, home, away = str(sp['possession_team']), str(sp['defensive_team']), str(sp['home_team_abbr']), str(sp['visitor_team_abbr'])
    hs, vs = int(sp['pre_snap_home_score']), int(sp['pre_snap_visitor_score'])
    diff = (hs - vs) if posT == home else (vs - hs)
    clk = str(sp['game_clock'])[:5].lstrip('0') or '0:00'
    desc = re.sub(r'^\([^)]*\)\s*', '', str(sp['play_description']))
    desc = re.sub(r'^\((Shotgun|No Huddle, Shotgun|No Huddle)\)\s*', '', desc)
    mm, dd_, yy = str(sp['game_date']).split('/')
    import datetime
    date = datetime.date(int(yy), int(mm), int(dd_))
    key = f'2023_{posT}_{g}_{play_id}'
    return key, {
        'key': key, 'real': True, 'src': 'bdb2026', 'noNum': True, 'season': 2023, 'round': f"Week {int(sp['week'])}", 'date': date.strftime('%b %-d, %Y'),
        'home': home, 'away': away, 'offT': posT, 'defT': defT, 'offName': TEAMS.get(posT, posT), 'defName': TEAMS.get(defT, defT),
        'down': down, 'dist': int(sp['yards_to_go']), 'ytg': ytg,
        'clock': f"Q{int(sp['quarter'])} · {clk} · " + ('tied' if diff == 0 else ('up ' if diff > 0 else 'down ') + str(abs(diff))),
        'score': [hs, vs], 'T': round(T, 2), 'qb': qb, 'off': off, 'def': de,
        'pro': {'targetNum': tgt['num'], 'spot': {'x': r2(spot[0]), 'y': r2(spot[1])}, 'type': typ, 'result': {'kind': kind, 'yac': yac},
                'text': desc, 'gain': gain, 'air': round(air, 2)},
        'targetName': tgt['name'], 'coverage': str(sp.get('team_coverage_type') or ''),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--weeks', default='', help='comma-separated week numbers (default: all)')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    sup = pd.read_csv(os.path.join(SRC, 'supplementary_data.csv'), low_memory=False).set_index(['game_id', 'play_id'])
    weeks = [int(w) for w in a.weeks.split(',')] if a.weeks else sorted(int(re.search(r'w(\d+)', f).group(1)) for f in glob.glob(os.path.join(SRC, 'input_2023_w*.csv')))
    idx_path = os.path.join(OUT, 'index.json')
    index = {e[0]: e for e in json.load(open(idx_path))} if os.path.exists(idx_path) else {}
    skips, kept = {}, 0
    for w in weeks:
        inp = pd.read_csv(os.path.join(SRC, f'input_2023_w{w:02d}.csv'))
        outp = pd.read_csv(os.path.join(SRC, f'output_2023_w{w:02d}.csv'))
        og = {k: v for k, v in outp.groupby(['game_id', 'play_id'])}
        for (g, p), df in inp.groupby(['game_id', 'play_id']):
            try:
                sp = sup.loc[(g, p)] if (g, p) in sup.index else None
                key, play = convert_play(g, p, df, og.get((g, p)), sp)
            except Skip as e:
                skips[str(e)] = skips.get(str(e), 0) + 1
                continue
            except Exception as e:
                skips['error: ' + type(e).__name__] = skips.get('error: ' + type(e).__name__, 0) + 1
                continue
            json.dump(play, open(os.path.join(OUT, key + '.json'), 'w'), separators=(',', ':'))
            # index row: key, QB, offense, defense, down, distance, yards to goal, week
            index[key] = [key, play['qb']['name'], play['offT'], play['defT'], play['down'], play['dist'], play['ytg'], w]
            kept += 1
        print(f'week {w}: total kept so far {kept}', flush=True)
    json.dump(sorted(index.values()), open(idx_path, 'w'), separators=(',', ':'))
    print('kept', kept, 'skipped', skips, '| index has', len(index), 'plays')


if __name__ == '__main__':
    main()
