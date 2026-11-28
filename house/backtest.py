"""The House back-tests, first round: how well each version of the district equation places the races once the national
House vote is known. Each election 2012-2024 is forecast from the others (left out of the fit), given that year's actual
national vote, so the test measures the districts alone; the national vote's own error is added later.

Versions, each adding to the one before:
    lean        each district at the national vote plus its lean (Cook's PVI as published), no fitting
    fitted      the lean's weight fitted
    incumbents  + a Democratic or a Republican member on the ballot
    last        + the district's last result on the same lines (against that year's nation)
    moved       + a member running where the lines are new to them counts for less
    money       + each side's money (FEC receipts over the cycle, as a log ratio)

Races: those both parties contested, with a lean published for the lines in use (2024's stale ones are left out).
Seats: every seat, the uncontested ones to the party that held them.

    python house/backtest.py
"""
import os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
T = pd.read_csv(os.path.join(ROOT, 'data', 'house', 'training.csv'))
T['has_prev'] = T.prev.notna().astype(int); T['prev0'] = T.prev.fillna(0)
T['money'] = np.log1p(T.dem_money.fillna(0)) - np.log1p(T.rep_money.fillna(0)); T['has_money'] = (T.dem_money.notna() & T.rep_money.notna()).astype(int)
T['money'] = np.where(T.has_money == 1, T.money, 0)
T['inc_d_moved'] = T.inc_d * T.moved; T['inc_r_moved'] = T.inc_r * T.moved
T['inc_d_new'] = T.inc_d * T.redrawn; T['inc_r_new'] = T.inc_r * T.redrawn
VERSIONS = {'lean': None, 'fitted': ['pvi'], 'incumbents': ['pvi', 'inc_d', 'inc_r'], 'last': ['pvi', 'inc_d', 'inc_r', 'prev0', 'has_prev'],
            'moved': ['pvi', 'inc_d', 'inc_r', 'prev0', 'has_prev', 'inc_d_new', 'inc_r_new'],
            'money': ['pvi', 'inc_d', 'inc_r', 'prev0', 'has_prev', 'inc_d_new', 'inc_r_new', 'money', 'has_money']}
YEARS = sorted(T.year.unique())
use = T.contested & T.pvi.notna() & ~T.pvi_stale.astype(bool)


def fit(a, cols):
    X = np.column_stack([np.ones(len(a))] + [a[c].values for c in cols]); y = (a.dem2 - a.national).values
    return np.linalg.lstsq(X, y, rcond=None)[0]


def predict(b, a, cols):
    return a.national.values + np.column_stack([np.ones(len(a))] + [a[c].values for c in cols]) @ b


def run(name, cols):
    rows = []
    for y in YEARS:
        test = T[(T.year == y)]
        if cols is None: f = test.national + test.pvi.fillna(0)
        else: f = pd.Series(predict(fit(T[use & (T.year != y)], cols), test, cols), index=test.index)
        m = use[test.index]; e = (f - test.dem2)[m]
        called = int(((f > 50) == (test.dem2 > 50))[m].sum())
        seats_d = int((f[test.contested] > 50).sum() + (test.winner[~test.contested] == 'D').sum()); real = int((test.winner == 'D').sum())
        rows.append({'year': y, 'races': int(m.sum()), 'miss': float(e.abs().mean()), 'called': called, 'seats_d': seats_d, 'actual': real})
    r = pd.DataFrame(rows)
    return {'version': name, 'typical miss': round(r.miss.mean(), 2), 'called': f'{r.called.sum()} of {r.races.sum()}', 'seat miss': round((r.seats_d - r.actual).abs().mean(), 1),
            'by year': ' '.join(f"{y}:{m:.1f}/{s - a:+d}" for y, m, s, a in zip(r.year, r.miss, r.seats_d, r.actual))}


if __name__ == '__main__':
    out = pd.DataFrame([run(k, v) for k, v in VERSIONS.items()]); print(out.to_string(index=False))
    b = fit(T[use], VERSIONS['money']); print('\nfitted on every year:', dict(zip(['const'] + VERSIONS['money'], b.round(3))))
