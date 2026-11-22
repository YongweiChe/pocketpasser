"""Learn the game's catch / interception odds from ~14k real 2023 throws and write them into index.html.

Input: CSV from tools/dump_features.js (the game's own geometry for each pro throw + what really happened).
Model: multinomial logistic regression (complete / incomplete / interception) on the game's features.
Validation: train weeks 1-14, test weeks 15-18, versus the old hand-tuned odds (log loss, Brier, calibration).
Only the fitted coefficients ship (no play data). Usage:
  node tools/dump_features.js /tmp/feat.csv && python3 tools/fit_completion.py /tmp/feat.csv [--write]
"""
import json, os, re, sys
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = ['complete', 'incomplete', 'int']


def features(f):
    """Must match cpOdds() in index.html exactly (same order, same clipping)."""
    gr = f.gr.clip(0, 4); gd = f.gd.clip(0, 10); d = f.d.clip(0, 60)
    return np.column_stack([gr, (gr > .05).astype(float), np.log1p(gd), (gd < 1).astype(float), f.behind, f.lane,
                            d / 10, (d / 10) ** 2, f.fast, f.depth.clip(-10, 60) / 10])


NAMES = ['gr', 'gr>.05', 'log1p(gd)', 'gd<1', 'behind', 'lane', 'd/10', '(d/10)^2', 'fast', 'depth/10']


def scores(P, y):
    Y = np.eye(3)[y]
    return -np.mean(np.log(np.clip((P * Y).sum(1), 1e-6, 1))), np.mean(((P - Y) ** 2).sum(1))


def main():
    f = pd.read_csv(sys.argv[1])
    y = f.result.map({c: i for i, c in enumerate(CLASSES)}).values
    X = features(f)
    tr, te = f.week <= 14, f.week >= 15
    m = LogisticRegression(max_iter=2000, C=1.0).fit(X[tr], y[tr])
    Pn = m.predict_proba(X[te])
    hpc, hpi = f.hand_pC.values[te], f.hand_pI.values[te]
    Ph = np.column_stack([hpc, np.clip(1 - hpc - hpi, 0, 1), hpi])
    print(f'held-out weeks 15-18: {te.sum():,} throws (trained on {tr.sum():,})')
    for name, P in [('hand-tuned (old)', Ph), ('learned (new)', Pn)]:
        ll, br = scores(P, y[te])
        print(f'  {name:<17} log loss {ll:.3f}  Brier {br:.3f}  mean catch {P[:, 0].mean():.3f}  mean INT {P[:, 2].mean():.3f}')
    print(f'  actual                                               catch {np.mean(y[te] == 0):.3f}  INT {np.mean(y[te] == 2):.3f}')
    b = pd.cut(Pn[:, 0], [0, .3, .5, .6, .7, .8, .9, 1])
    cal = pd.DataFrame({'b': b, 'pred': Pn[:, 0], 'real': y[te] == 0}).groupby('b', observed=True).agg(n=('real', 'size'), pred=('pred', 'mean'), real=('real', 'mean'))
    print('learned model calibration on held-out throws:\n', cal.round(2).to_string())
    m = LogisticRegression(max_iter=2000, C=1.0).fit(X, y)   # final model on every week
    coef = {'b': [round(v, 5) for v in m.intercept_.tolist()], 'w': [[round(v, 5) for v in row] for row in m.coef_.tolist()]}
    print('coefficients (rows: complete, incomplete, int):')
    for i, c in enumerate(CLASSES): print(f'  {c:<10} b={coef["b"][i]:+.3f} ' + ' '.join(f'{n}={w:+.2f}' for n, w in zip(NAMES, coef['w'][i])))
    if '--write' in sys.argv:
        p = os.path.join(ROOT, 'index.html'); s = open(p).read()
        block = '/*CP_MODEL*/const CPM=' + json.dumps(coef, separators=(',', ':')) + ';/*CP_MODEL_END*/'
        if '/*CP_MODEL*/' not in s: sys.exit('index.html has no /*CP_MODEL*/ marker')
        s = re.sub(r'/\*CP_MODEL\*/.*?/\*CP_MODEL_END\*/', lambda _: block, s, flags=re.S)
        open(p, 'w').write(s); print('wrote coefficients into index.html')


if __name__ == '__main__':
    main()
