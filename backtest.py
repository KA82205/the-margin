"""Runs the forecast as it would have stood on seven days before each election of 2008-2024 and scores it.

Every forecast uses only what existed on its day: polls that had ended, the two previous elections, and sizes of error and
fundamentals equations from earlier elections. (The Fifty-Two Keys count for a year uses that year's final data; most of it
is in hand by late summer. Final expert ratings and betting odds are added on the last day only.)
"""
import json, sys
import numpy as np, pandas as pd
import model as M, fundamentals as F

DAYS = [120, 90, 60, 30, 14, 7, 1]
YEARS = [2008, 2012, 2016, 2020, 2024]

def load():
    res = pd.read_csv('data/results.csv'); polls = pd.read_csv('data/polls.csv', parse_dates=['end']); errs = pd.read_csv('data/average_errors.csv')
    return res, polls, errs

def score(out, res, year):
    r = res[res.year == year].set_index('state'); S = out['states'].set_index('state')
    act = r.dem2.reindex(S.index); won = (act > 50).astype(float)
    dem_won = r.ev[r.dem2 > 50].sum() > r.ev.sum() / 2; p = out['p_dem']
    two = S.index.str.len() == 2
    return {'p_dem': p, 'p_winner': p if dem_won else 1 - p, 'called': bool((p > 0.5) == dem_won), 'national': out['national'], 'national_error': out['national'] - r.nat2.iloc[0],
            'ev': out['ev_mean'], 'ev_median': out['ev_median'], 'ev_lo': out['ev_lo'], 'ev_hi': out['ev_hi'], 'national_actual': float(r.nat2.iloc[0]), 'ev_actual': int(r.ev[r.dem2 > 50].sum()), 'state_mae': float((S['mean'] - act)[two].abs().mean()), 'state_bias': float((S['mean'] - act)[two].mean()),
            'states_called': int(((S.p_dem > 0.5) == (won > 0.5)).sum()), 'of': int(len(S)), 'brier': float(((S.p_dem - won) ** 2).mean()),
            'states51_called': int(((S.p_dem > 0.5) == (won > 0.5))[two].sum()), 'brier51': float(((S.p_dem - won) ** 2)[two].mean()),
            'missed': sorted(S.index[(S.p_dem > 0.5) != (won > 0.5)]),
            'cover80': float(((act >= S['mean'] - 1.2816 * np.sqrt(S.sd ** 2 + out['national_sd'] ** 2)) & (act <= S['mean'] + 1.2816 * np.sqrt(S.sd ** 2 + out['national_sd'] ** 2)))[two].mean())}

def implied():
    """Share of the vote each rating points to: three points a step from a toss-up; solid states are left alone."""
    rt = pd.read_csv('data/ratings.csv'); out = {}
    for y, g in rt.groupby('year'):
        out[int(y)] = {s: (50 + 3 * (4 - r) if 1.5 < r < 6.5 else None) for s, r in zip(g.state, g.rating)}
    return out

def run(days=DAYS, ratings=False, settings=None, keep_states=False):
    old = dict(M.SET)
    if settings: M.SET.update(settings)
    res, polls, errs = load(); t = F.table(); rows = []; states = []
    rt = implied() if ratings else {}
    for y in YEARS:
        tables = M.error_tables(y, res, errs); fd, fsd, parts = F.forecast(y, t); ev = M.ev_table(y, res)
        for d in days:
            asof = pd.Timestamp(M.ELECTION[y]) - pd.Timedelta(days=d)
            out, info = M.forecast(y, asof, polls, res, tables, (fd, fsd), ratings=rt.get(y) if d <= 7 else None, ev=ev)
            s = score(out, res, y); s.update(year=y, days=d, p_model=out['p_model'], **info); rows.append(s)
            if keep_states and d == 1:
                r = res[res.year == y].set_index('state')
                for q in out['states'].itertuples():
                    states.append({'year': y, 'state': q.state, 'p_dem': q.p_dem, 'mean': q.mean, 'actual': float(r.dem2[q.state]), 'poll_weight': q.poll_weight})
    M.SET.clear(); M.SET.update(old)
    R = pd.DataFrame(rows)
    return (R, pd.DataFrame(states)) if keep_states else R

if __name__ == '__main__':
    R, ST = run(keep_states=True)
    ST.to_csv('data/backtest_states.csv', index=False)
    pd.set_option('display.width', 250)
    print(R[['year', 'days', 'p_dem', 'p_winner', 'called', 'national', 'national_error', 'ev', 'ev_actual', 'state_mae', 'state_bias', 'states_called', 'brier', 'cover80', 'poll_share']].round(3).to_string(index=False))
    print(R.groupby('days').agg(called=('called', 'sum'), p_winner=('p_winner', 'mean'), nat_abs=('national_error', lambda x: x.abs().mean()), state_mae=('state_mae', 'mean'), states=('states_called', 'sum'), brier=('brier', 'mean'), cover80=('cover80', 'mean')).round(3).to_string())
    print(R[R.days == 1][['year', 'missed']].to_string(index=False))
    R.drop(columns=['missed']).to_csv('data/backtest.csv', index=False)
