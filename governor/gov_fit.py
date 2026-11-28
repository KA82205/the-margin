"""The live governor forecast's fitted pieces, data/governor/model.json, and the back-tests, data/governor/backtest.json.
Run when an election is added to the training table (gov_after.py), and by hand after a change to the method.

    each race's equation   the Democratic share = the year's level + weights on the state's lean and on a sitting
                           governor of either party on the November ballot, fitted with a level for each year on every
                           even year from FIRST (2006) in the training table
    the year's level       50 + alpha + beta x (the national House vote - 50), fitted on those years' levels; the forecast
                           puts the national mood where the House vote is
    the shared error       at each distance: beta x the national mood's miss of the House vote in every year it was read
                           (the Senate model's mood), with the levels' own spread about the line
    each race's error      the spread of the fit's misses
    polls                  each race's polling average (gov_polls.py) blended in as the Senate's are, fitted at each
                           distance on the races polled (FiveThirtyEight's archive, 2018-2024; Wikipedia after)
    governors who run      the share of governors free to run again (not term-limited) who were on the November ballot,
                           from Wikipedia's account of each year's races
    the back-tests         each year with a national mood forecast from the other years, with and without the polls

    python governor/gov_fit.py
"""
import glob, json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gov_simulate as S

D = os.path.join(ROOT, 'data', 'governor')


def years_fitted(T):
    return [int(y) for y in sorted(T.year.unique()) if y >= S.FIRST and y % 2 == 0 and T[(T.year == y) & T.usable].shape[0] >= 8]


def senate_simulation():
    ps = sorted(glob.glob(os.path.join(ROOT, 'data', 'senate', '[0-9]' * 4, 'model.json')))
    return json.load(open(ps[-1]))['simulation']


def governors_who_ran(T, years):
    """Of the governors free to run again (the status does not say term-limited), the share on the November ballot."""
    t = T[T.year.isin(years) & T.governor.notna()]
    free = t[~t.status.fillna('').str.contains('term-limited|term limited|term-limit', case=False)]
    on = (free.inc_d + free.inc_r) > 0
    return round(float(on.mean()), 4) if len(free) else None, int(len(free))


def model(T, years):
    w, lev, sd = S.fit(T, years)
    N = S.national(); nv = S.votes()
    alpha, beta, lsd = S.level_line(lev, nv)
    dist, polls = {}, {}
    for d in S.DAYS:
        e = N[(N.days == d) & N.vote.notna()].assign(e=lambda g: g.mood - g.vote)
        dist[str(d)] = {'mood_rmse': round(float(np.sqrt(np.mean(e.e ** 2))), 4), 'shared_sd': round(float(np.sqrt(beta ** 2 * np.mean(e.e ** 2) + lsd ** 2)), 4),
                        'mood_years': [int(y) for y in e.year]}
        (w0, w1, k), own, n = S.poll_fit(S.with_polls(T, d), years, w, alpha, beta, N, d)
        polls[str(d)] = {'w0': w0, 'w1': w1, 'k': round(k, 4), 'own_sd': round(own, 4) if own is not None else None, 'races': n}
    ran, free = governors_who_ran(T, years)
    sim = senate_simulation()
    return {'note': 'The live governor forecast\'s fitted pieces (governor/gov_fit.py). Shares are the Democratic two-party share, in points.',
            'years': years, 'columns': S.COLS, 'coef': {c: round(float(v), 5) for c, v in zip(S.COLS, w)}, 'race_sd': round(sd, 4),
            'levels': {str(y): round(float(lev[y]), 4) for y in years}, 'votes': {str(y): float(nv[y]) for y in years if y in nv.index},
            'alpha': round(alpha, 4), 'beta': round(beta, 4), 'level_sd': round(lsd, 4), 'distances': dist, 'polls': polls,
            'governors_ran': ran, 'governors_free': free,
            'simulation': {'t_df': S.T_DF, 'pres_link': sim['pres_link'], 'shared_floor': sim['shared_floor'], 'own_floor': sim['own_floor']}}


def records(df):
    """Rows for a JSON file, a missing value as null."""
    df = df.round(4)
    return df.astype(object).where(pd.notna(df), None).to_dict('records')


def backtest(T, years, keep):
    R, X = S.run(polls=True, T0=T, fit_years=years); R0, _ = S.run(polls=False, T0=T, fit_years=years)
    s, s0 = S.summary(R), S.summary(R0)
    summ = lambda x: {str(int(d)): {k: round(float(v), 4) for k, v in row.items()} for d, row in x.iterrows()}
    tested = []
    last, first = s.loc[1], s0.loc[1]
    tested.append({'idea': 'Race polls, blended in as the Senate\'s are: more of the weight the more polling there is, up to a cap, fitted at each distance',
                   'result': f'On the last day, {int(last.called)} of {int(last.races)} races called against {int(first.called)} without them, a typical miss of {last.avg_miss:.1f} points '
                             f'against {first.avg_miss:.1f}, and a Brier score of {last.brier:.3f} against {first.brier:.3f}', 'adopted': bool(last.brier <= first.brier)})
    tests = {k: v for k, v in (keep or {}).items() if int(k) not in set(R.year)}
    return {'note': 'Each election forecast from the other elections at each distance from election day; governorships are the Democrats\' among the year\'s races.',
            'years': sorted(int(y) for y in R.year.unique()), 'fit_years': years,
            'rows': R[['year', 'days', 'races', 'called', 'avg_miss', 'brier', 'dem_won_mean', 'dem_won_low', 'dem_won_high', 'dem_won', 'inside']].round(4).to_dict('records'),
            'races': records(X[X.days.isin([365, 120, 60, 14, 1])]),
            'summary': summ(s), 'summary_without_polls': summ(s0), 'tests': tests, 'tested': tested + TESTED}


# ideas tried while building the governor model, beyond those the back-test above measures each time it is run
TESTED = []


def main():
    T = S.load(); years = years_fitted(T)
    m = model(T, years)
    with open(os.path.join(D, 'model.json'), 'w') as f: json.dump(m, f, indent=1)
    bp = os.path.join(D, 'backtest.json'); old = json.load(open(bp)) if os.path.exists(bp) else {}
    b = backtest(T, years, old.get('tests'))
    with open(bp, 'w') as f: json.dump(b, f, indent=1)
    print('fitted on', years, '| weights', m['coef'], '| race sd', m['race_sd'], '| level line', m['alpha'], m['beta'], m['level_sd'], '| governors who ran', m['governors_ran'], m['governors_free'])
    print('shared sd', {d: v['shared_sd'] for d, v in m['distances'].items()}); print('polls', m['polls'])
    print(pd.DataFrame(b['summary']).T.to_string()); print(pd.DataFrame(b['summary_without_polls']).T.to_string())
    return m


if __name__ == '__main__':
    main()
