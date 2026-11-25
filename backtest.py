"""Runs the forecast as it would have stood on seven days before each election of 2008-2024 and scores it.

Every forecast uses only what existed on its day: polls that had ended, the two previous elections, and sizes of error and
equations from earlier elections. The run goes through the same code as the live forecast, with every part the live forecast
has:

    polls                  as they stood on the day
    the national prior     the fundamentals forecast, made from earlier elections
    state-level models     the Tipping Point Nowcast's forecast of each state (data/state_models.csv)
    the error sizes        from elections before the one being forecast

What could not be rebuilt as it stood on the day, and is used all the same or left out (README, "What the back-test cannot
show"):
    - the state-level models have one forecast a year on record, not one a day. The approval model's is made about 100 days
      out, so at 120 days the test sees it three weeks early. For 2020 and 2024 they are the forecasts the authors published;
      for 2008, 2012 and 2016 each model was refitted on the elections before.
    - the Fifty-Two Keys count for a year uses that year's final figures, most of them in hand by late summer, and today's
      revised economic data.
    - betting odds are not in the back-test: checkable election-eve odds for 2008-2024 have not been collected.

    python backtest.py                 the published forecast (writes data/backtest.csv, data/backtest_states.csv)
    python backtest.py candidate       the candidate under review (writes data/backtest_candidate.csv)
"""
import json, sys
import numpy as np, pandas as pd
import model as M, fundamentals as F

DAYS = [120, 90, 60, 30, 14, 7, 1]
YEARS = [2008, 2012, 2016, 2020, 2024]
VERSIONS = {'published': {}, 'candidate': M.CANDIDATE}

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

def state_models(year):
    """What the Tipping Point Nowcast's two state-level models, averaged, said of each state and of the country."""
    g = pd.read_csv('data/state_models.csv'); g = g[g.year == year].dropna(subset=['average'])
    return dict(zip(g.state, g.average)), {r.state: (r.approval_economy, r.long_range_polls) for r in g.itertuples()}

def run(days=DAYS, ratings=False, settings=None, keep_states=False, version='published', with_state_models=True):
    old = dict(M.SET); M.SET.update(VERSIONS[version])
    if settings: M.SET.update(settings)
    res, polls, errs = load(); t = F.table(); rows = []; states = []
    rt = implied() if ratings else {}
    need_timeline = M.SET['poll_weight'] == 'timeline' or M.SET['state_poll_weight'] == 'horizon'
    if need_timeline: import timeline as T
    for y in YEARS:
        tables = M.error_tables(y, res, errs); fd, fsd, parts = F.forecast(y, t); ev = M.ev_table(y, res)
        extra, two = state_models(y)
        tl = T.curves(y) if need_timeline else None
        E, D, K = two['US'][0], two['US'][1], parts['keys_model']
        for d in days:
            asof = pd.Timestamp(M.ELECTION[y]) - pd.Timedelta(days=d)
            # the candidate's prior holds the long-range model, which is built on the national polls of the October before:
            # as long as those still weigh in the polling average they are counted once, not twice (model.long_range_weight)
            weight, carried = M.long_range_weight(y, asof, tl, polls) if need_timeline else (1.0, 0.0)
            prior = {'fundamentals': fd, 'three_models': F.three_models(E, D, K, weight),
                     'four_models': (E + D + K + parts['approval_model']) / 4}[M.SET['national_prior']]      # four_models: a check only, the approval equation as a fourth
            carried = {'fundamentals': 0.0, 'three_models': carried, 'four_models': 0.75 * carried}[M.SET['national_prior']]
            # the second figure is the prior's error. Under the 'timeline' rule the error of the whole mix comes from the record
            # and this is only what the prior's inputs may still drift by: nothing here, they are each year's final inputs.
            # Under the published rule it is the fundamentals forecast's own error, whichever prior is being tried.
            fund = (prior, 0.0 if M.SET['poll_weight'] == 'timeline' else fsd)
            out, info = M.forecast(y, asof, polls, res, tables, fund, ratings=rt.get(y) if d <= 7 else None, ev=ev, extra_prior=extra if with_state_models else None, timeline=tl, prior_poll_load=carried)
            s = score(out, res, y); s.update(year=y, days=d, p_model=out['p_model'], **info); rows.append(s)
            if keep_states and d == 1:
                r = res[res.year == y].set_index('state')
                for q in out['states'].itertuples():
                    states.append({'year': y, 'state': q.state, 'p_dem': q.p_dem, 'mean': q.mean, 'actual': float(r.dem2[q.state]), 'poll_weight': q.poll_weight})
    M.SET.clear(); M.SET.update(old)
    R = pd.DataFrame(rows)
    return (R, pd.DataFrame(states)) if keep_states else R

def summary(R):
    return R.groupby('days').agg(called=('called', 'sum'), p_winner=('p_winner', 'mean'), nat_abs=('national_error', lambda x: x.abs().mean()), state_mae=('state_mae', 'mean'), states=('states_called', 'sum'),
                                 brier=('brier', 'mean'), cover80=('cover80', 'mean'), poll_share=('poll_share', 'mean')).sort_index(ascending=False)

if __name__ == '__main__':
    version = 'candidate' if 'candidate' in sys.argv else 'published'
    R, ST = run(keep_states=True, version=version)
    pd.set_option('display.width', 250)
    print(version)
    print(R[['year', 'days', 'p_dem', 'p_winner', 'called', 'national', 'national_error', 'ev_median', 'ev_actual', 'state_mae', 'state_bias', 'states_called', 'brier', 'cover80', 'poll_share']].round(3).to_string(index=False))
    print(summary(R).round(3).to_string())
    print(R[R.days == 1][['year', 'missed']].to_string(index=False))
    if version == 'published':
        ST.to_csv('data/backtest_states.csv', index=False); R.drop(columns=['missed']).to_csv('data/backtest.csv', index=False)
    else:
        R.drop(columns=['missed']).to_csv('data/backtest_candidate.csv', index=False)
