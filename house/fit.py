"""The live House forecast's fitted pieces, data/house/model.json, and the back-tests, data/house/backtest.json. Run when
an election is added to the training table (after_election.py), and by hand after a change to the method.

    the district equation   each contested district's Democratic share = the year's level + weights on the district's
                            lean and on a member of either party on the ballot, fitted on every election from 2018 in the
                            training table, with a level for each year (simulate.fit)
    the gap                 each year's level less its national House vote (data/senate/national_fundamentals.csv),
                            averaged; its spread goes into the shared error
    the shared error        at each distance from election day: the national mood's miss of the House vote in every year
                            it was read (the Senate model's mood, data/senate/training_rows.csv), with the gap's spread
    each district's error   the spread of the fit's misses
    members                 the share of seats whose member was on the November ballot, and the share of members who ran
                            who lost their primary (data/house/members.csv), from 2018
    redrawn maps            the spread between the lean Cook published for a district before its map was redrawn and the
                            lean on the new lines (2024's redrawn states), added to a district's error while its lean
                            predates its map
    the back-tests          each fitted year forecast from the others at each distance, scored on the seats and on each
                            race's winner (simulate.run); a year read before its shares were all in is kept as a test of
                            that year from the years before it (after_election.py --test)

    python house/fit.py
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import simulate as S

D = os.path.join(ROOT, 'data', 'house')
COLS = ['lean', 'inc_d', 'inc_r']
FIRST = 2018


def years_fitted(T):
    return [int(y) for y in sorted(T.year.unique()) if y >= FIRST and T[(T.year == y) & T.usable].dem2.notna().sum() > 300]


def redraw_sd(T):
    """The spread between 2024's stale leans (Cook's for the old lines) and the leans on the new lines."""
    A = pd.read_csv(os.path.join(D, 'leans_alt.csv')).set_index(['lines', 'state', 'district']).lean
    t = T[(T.year == 2024) & T.pvi_stale.astype(bool) & T.pvi.notna()]
    d = [p - A[(2024, s, k)] for s, k, p in zip(t.state, t.district, t.pvi) if (2024, s, k) in A.index]
    return round(float(np.std(d, ddof=1)), 3), len(d)


def model(T, years):
    w, lev, sd = S.fit(T, years, COLS)
    N = S.national(); nv = N.drop_duplicates('year').set_index('year').vote
    gaps = {y: float(lev[y] - nv[y]) for y in years}; gap, gap_sd = float(np.mean(gaps.values() and list(gaps.values()))), float(np.std(list(gaps.values()), ddof=1))
    dist = {}
    for d in S.DAYS:
        e = N[(N.days == d) & N.vote.notna()].assign(e=lambda g: g.mood - g.vote)
        dist[str(d)] = {'mood_rmse': round(float(np.sqrt(np.mean(e.e ** 2))), 4), 'mood_bias': round(float(e.e.mean()), 4),
                        'shared_sd': round(float(np.sqrt(np.mean(e.e ** 2) + gap_sd ** 2)), 4), 'mood_years': [int(y) for y in e.year]}
    M = pd.read_csv(os.path.join(D, 'members.csv')); M = M[M.year >= FIRST]
    rs, rn = redraw_sd(T)
    sim = json.load(open(os.path.join(ROOT, 'data', 'senate', '2028', 'model.json')))['simulation']
    return {'note': 'The live House forecast\'s fitted pieces (house/fit.py). Shares are the Democratic two-party share, in points.',
            'years': years, 'columns': COLS, 'coef': {c: round(float(v), 5) for c, v in zip(COLS, w)}, 'district_sd': round(sd, 4),
            'levels': {str(y): round(float(lev[y]), 4) for y in years}, 'votes': {str(y): float(nv[y]) for y in years},
            'gap': round(gap, 4), 'gap_sd': round(gap_sd, 4), 'distances': dist,
            'members': {'run_share': round(float(M.on_ballot.sum() / M.seats_with_member.sum()), 4),
                        'primary_loss': round(float(M.lost_primary.sum() / (M.on_ballot.sum() + M.lost_primary.sum())), 4), 'years': [int(y) for y in M.year]},
            'redraw_sd': rs, 'redraw_districts': rn,
            'simulation': {'t_df': S.T_DF, 'pres_link': sim['pres_link'], 'shared_floor': sim['shared_floor'], 'own_floor': sim['own_floor']}}


# each idea tried while building the House model, what the tests showed when it was tried, and whether it went in
# (house/backtest.py: each election placed from the others given its national vote; house/simulate.py: the forecast)
TESTED = [
    {'idea': 'Each district at the national vote plus its lean, nothing fitted', 'result': 'A typical contested race missed by 3.7 points, 2012-2024, even with the national vote known', 'adopted': False},
    {'idea': 'The lean\'s weight fitted', 'result': 'A typical miss of 3.6 points', 'adopted': True},
    {'idea': 'A member of either party on the November ballot', 'result': 'A typical miss of 3.2 points and 60 more races called, 2012-2024', 'adopted': True},
    {'idea': 'Fitted on 2018 onward rather than 2012 onward', 'result': 'A member was worth about 4 to 7 points to their party in 2012-2016 and about 2 to 3 since 2018: the House has become national, so the older years would overstate it', 'adopted': True},
    {'idea': 'Leans for 2018 and 2020 worked out the way Cook has since 2022 (three parts the last presidential election, one part the one before)', 'result': 'Brier score 0.032 against 0.035 with the even split Cook published then, and eight more races called; it is the lean the live forecast reads', 'adopted': True},
    {'idea': 'The district\'s last House result on the same lines', 'result': 'Added nothing once the lean and the member were in (a typical miss of 3.3 points against 3.2)', 'adopted': False},
    {'idea': 'A member running on lines new to them counting for less', 'result': 'A typical miss of 3.4 points against 3.2', 'adopted': False},
    {'idea': 'Money raised over the whole cycle', 'result': 'A little help in close races, but a forecast cannot know the totals in advance, and the typical miss was 3.3 points against 3.2', 'adopted': False},
    {'idea': 'Money as it stood on each day (every FEC report of both parties\' candidates, 2012-2024, about 70,000)', 'result': 'The forecasts of 2018-2024 barely moved: the seat count\'s typical miss fell by half a seat at some distances and not at others, and the races called and the chances stayed the same', 'adopted': False},
]


def backtest(T, years, keep):
    r = S.run(COLS, T0=T, tests=years, train=years)
    s = S.summary(r)
    rows = r[['year', 'days', 'seats_mid', 'actual', 'low80', 'high80', 'p_majority', 'called', 'races', 'brier', 'level']].round(4).to_dict('records')
    tests = {k: v for k, v in (keep or {}).items() if int(k) not in years}
    return {'note': 'Each election forecast from the other elections at each distance from election day; seats are the Democrats\'.',
            'years': years, 'rows': rows, 'summary': {str(int(d)): {k: round(float(v), 4) for k, v in x.items()} for d, x in s.iterrows()}, 'tests': tests, 'tested': TESTED}


def main():
    T = S.load(cook75=True); years = years_fitted(T)
    m = model(T, years)
    with open(os.path.join(D, 'model.json'), 'w') as f: json.dump(m, f, indent=1)
    bp = os.path.join(D, 'backtest.json'); old = json.load(open(bp)) if os.path.exists(bp) else {}
    b = backtest(T, years, old.get('tests'))
    with open(bp, 'w') as f: json.dump(b, f, indent=1)
    print('fitted on', years, '| weights', m['coef'], '| district sd', m['district_sd'], '| gap', m['gap'], m['gap_sd'])
    print('shared sd by distance', {d: v['shared_sd'] for d, v in m['distances'].items()}, '| members', m['members'], '| redraw sd', m['redraw_sd'], m['redraw_districts'])
    print(pd.DataFrame(b['summary']).T.to_string())
    return m


if __name__ == '__main__':
    main()
