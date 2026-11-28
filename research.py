"""Numbers for the Research tab that are not about the model: how far polling averages have stood from the result.
Writes data/research.json. Uses FiveThirtyEight's published polling averages for 1972-2016 (data/average_errors.csv)."""
import json
import numpy as np, pandas as pd

e = pd.read_csv('data/average_errors.csv')
H = [150, 120, 90, 60, 30, 14, 7, 1]
by_day = []
for d in H:
    n = e[(e.st == 'US') & (e.days == d)]; s = e[(e.st != 'US') & (e.days == d)]
    by_day.append({'days': d, 'national': round(float(2 * n.err.abs().mean()), 1), 'states': round(float(2 * s.err.abs().mean()), 1), 'elections': int(n.cycle.nunique()), 'state_averages': int(len(s))})
last = e[(e.st == 'US') & (e.days == 1)].sort_values('cycle')
by_year = [{'year': int(r.cycle), 'polls': round(float(2 * (r.avg - 50)), 1), 'result': round(float(2 * (r.res - 50)), 1), 'miss': round(float(2 * r.err), 1)} for r in last.itertuples()]
dem = sum(1 for r in by_year if r['miss'] > 0)
out = {'by_day': by_day, 'by_year': by_year, 'toward_dem': dem, 'years': len(by_year), 'mean_signed': round(float(np.mean([r['miss'] for r in by_year])), 1)}
json.dump(out, open('data/research.json', 'w'), indent=1)
print(by_day); print(by_year); print(dem, len(by_year), out['mean_signed'])

# ------------------------------------------------------------------------------------------------ further studies
import itertools
import fundamentals as F
res = pd.read_csv('data/results.csv')
NAMES = pd.read_csv('data/state_region_crosswalk.csv') if False else None

# 1 The Electoral College's tilt: the margin in the state that decided each election, against the national margin
tilt = []
for y, g in res.groupby('year'):
    g = g.sort_values('dem2', ascending=False); total = g.ev.sum(); dem_ev = g.ev[g.dem2 > 50].sum()
    o = g if dem_ev > total / 2 else g.iloc[::-1]
    tp = o[(o.ev.cumsum() > total / 2).values].iloc[0]
    tilt.append({'year': int(y), 'state': tp.state, 'state_margin': round(float(2 * (tp.dem2 - 50)), 1), 'national': round(float(2 * (g.nat2.iloc[0] - 50)), 1),
                 'tilt': round(float(2 * (tp.dem2 - g.nat2.iloc[0])), 1), 'winner': 'D' if dem_ev > total / 2 else 'R'})
out['tilt'] = {'years': tilt, 'toward_rep': sum(1 for x in tilt if x['tilt'] < -0.05), 'toward_dem': sum(1 for x in tilt if x['tilt'] > 0.05),
               'typical': round(float(np.mean([abs(x['tilt']) for x in tilt])), 1), 'largest': max(tilt, key=lambda x: abs(x['tilt']))}

# 2 Approval and the vote: the president's net approval in June against the party's share in November
t = F.table()
r = float(np.corrcoef(t.juneapp, t.incvote)[0, 1]); slope, icept = np.polyfit(t.juneapp, t.incvote, 1)
loo = []
for i in range(len(t)):
    m = np.arange(len(t)) != i; b1, b0 = np.polyfit(t.juneapp[m], t.incvote[m], 1); loo.append(float(t.incvote[i] - (b0 + b1 * t.juneapp[i])))
out['approval'] = {'points': [{'year': int(a.year), 'net': float(a.juneapp), 'share': round(float(a.incvote), 1), 'party': 'D' if a.deminc else 'R', 'miss': round(e, 1)} for a, e in zip(t.itertuples(), loo)],
                   'r': round(r, 2), 'slope10': round(float(10 * slope), 1), 'at_zero': round(float(icept), 1), 'miss': round(float(np.mean(np.abs(loo))), 1),
                   'side': int(sum(((a.incvote - e) > 50) == (a.incvote > 50) for a, e in zip(t.itertuples(), loo))), 'n': int(len(t)),
                   'even_at': round(float((50 - icept) / slope), 0)}

# 3 Which states are moving: each state's lean (its margin less the national margin), 2012 against 2024
st = res[res.state.str.len() == 2].copy(); st['lean'] = 2 * (st.dem2 - st.nat2)
L = st.pivot(index='state', columns='year', values='lean')
move = (L[2024] - L[2012]).dropna().sort_values()
close = lambda y: int(((2 * (st[st.year == y].dem2 - 50)).abs() < 5).sum())
out['movers'] = {'states': [{'state': s, 'from': round(float(L[2012][s]), 1), 'to': round(float(L[2024][s]), 1), 'move': round(float(v), 1)} for s, v in move.items()],
                 'toward_rep': int((move < -1).sum()), 'toward_dem': int((move > 1).sum()),
                 'close': [{'year': int(y), 'n': close(y), 'ev': int(st[(st.year == y) & ((2 * (st.dem2 - 50)).abs() < 5)].ev.sum())} for y in sorted(st.year.unique())],
                 'persist': round(float(np.corrcoef(L[2020].dropna(), L[2024].dropna())[0, 1]), 3), 'persist_1976': round(float(np.corrcoef(L[1972].dropna(), L[1976].dropna())[0, 1]), 2)}

# 4 Do the polls miss everywhere at once? Final state polling averages against results, 1972 to 2016
s1 = e[(e.st != 'US') & (e.days == 1)].copy(); s1['m'] = 2 * s1.err
cyc = s1.groupby('cycle').m
shared = float(cyc.mean().var(ddof=0) / s1.m.var(ddof=0))                      # the part of the scatter that is one election-wide miss
wide = s1.pivot(index='cycle', columns='st', values='m'); wide = wide.loc[:, wide.notna().sum() >= 8]
cor = wide.corr(min_periods=8).values; pair = float(np.nanmean(cor[np.triu_indices_from(cor, 1)]))
out['together'] = {'years': [{'year': int(c), 'states': int(len(g)), 'mean': round(float(g.mean()), 1), 'same_side': round(float(max((g > 0).mean(), (g < 0).mean())), 2),
                              'spread': round(float(g.std(ddof=0)), 1)} for c, g in cyc], 'shared': round(shared, 2), 'pair': round(pair, 2), 'states': int(wide.shape[1])}

# 5 The primaries and November. New Hampshire: the share of the party in office's candidate less the challenger's share in his own primary.
p = pd.read_csv('data/nh_primaries.csv').merge(t[['year', 'incvote', 'deminc', 'term1']], on='year'); p['gap'] = p.office_share - p.challenger_share
took = {1952: 0, 1956: 1, 1960: 0, 1964: 1, 1968: 0, 1972: 1, 1976: 0, 1980: 0, 1984: 1, 1988: 1, 1992: 0, 1996: 1, 2000: 0, 2004: 1, 2008: 0, 2012: 1, 2016: 0, 2020: 0, 2024: 0}
p['won'] = p.year.map(took)
def walk(cols, first=1976):
    """Each election from `first` estimated from an equation fitted to the elections before it."""
    errs = {}
    for y in p.year[p.year >= first]:
        past, row = p[p.year < y], p[p.year == y].iloc[0]
        b = np.linalg.lstsq(np.column_stack([np.ones(len(past))] + [past[c] for c in cols]), past.incvote.values, rcond=None)[0]
        errs[int(y)] = float(b[0] + sum(bj * row[c] for bj, c in zip(b[1:], cols)) - row.incvote)
    return errs
pa = p.merge(t[['year', 'juneapp']], on='year'); p['juneapp'] = pa.juneapp.values
w_gap, w_app, w_both = walk(['gap', 'term1']), walk(['juneapp', 'term1']), walk(['juneapp', 'term1', 'gap'])
mae = lambda d, y0=1976: round(float(np.mean([abs(v) for y, v in d.items() if y >= y0])), 2)
# the published record of Helmut Norpoth's Primary Model, first used in 1996: (year, its call, the winner)
published = [(1996, 'Clinton', 'Clinton'), (2000, 'Gore', 'Bush'), (2004, 'Bush', 'Bush'), (2008, 'Obama', 'Obama'), (2012, 'Obama', 'Obama'), (2016, 'Trump', 'Trump'), (2020, 'Trump', 'Biden'), (2024, 'Harris', 'Trump')]
out['primary'] = {'points': [{'year': int(a.year), 'gap': int(a.gap), 'share': round(float(a.incvote), 1), 'won': int(a.won), 'who': a.office_ran, 'against': a.challenger} for a in p.itertuples()],
                  'r': round(float(np.corrcoef(p.gap, p.incvote)[0, 1]), 2), 'stronger_won': int(((p.gap > 0) == (p.won == 1)).sum()), 'n': int(len(p)),
                  'lost_nh': [int(y) for y in p.year[p.office_won == 0]], 'lost_nh_won': int(p.won[p.office_won == 0].sum()),
                  'published': [{'year': y, 'call': c, 'winner': w, 'right': c == w} for y, c, w in published], 'published_right': sum(c == w for _, c, w in published),
                  'walk': {'primary': mae(w_gap), 'approval': mae(w_app), 'both': mae(w_both), 'since2008': {'primary': mae(w_gap, 2008), 'approval': mae(w_app, 2008), 'both': mae(w_both, 2008)}, 'n': len(w_gap),
                           'better_with': [y for y in w_both if abs(w_both[y]) < abs(w_app[y])]}}
# sitting presidents on the New Hampshire ballot, and what became of their party in November
SITTING = [1952, 1956, 1964, 1968, 1972, 1976, 1980, 1984, 1992, 1996, 2004, 2012, 2020, 2024]
sit = p[p.year.isin(SITTING)]; weak, strong = sit[sit.office_share < 60], sit[sit.office_share >= 60]
out['primary']['sitting'] = {'n': int(len(sit)), 'weak': int(len(weak)), 'weak_won': int(weak.won.sum()), 'weak_years': [int(y) for y in weak.year], 'strong': int(len(strong)), 'strong_won': int(strong.won.sum()),
                             'strong_lost': [int(y) for y in strong.year[strong.won == 0]],
                             'points': [{'year': int(a.year), 'who': a.office_ran, 'share': int(a.office_share), 'won': int(a.won)} for a in sit.itertuples()]}
out['primary']['r_approval'] = out['approval']['r']

# 6 The states a year out: Jay DeSart's long-range model (data/desart.csv, from his replication data, tools/make_desart.py).
# Each state from its last result, national head-to-head polls of the October before the election year, home states and
# the consecutive terms of the party in the White House. Scored on the 50 states, 2008-2024, against the results here: his
# published forecasts for 2020 and 2024; for 2008-2016 the model refitted on the elections before each one (his October
# polls for those years are of the two eventual nominees, which no one knew a year out). Beside it: every state voting as
# it did four years before; that map moved evenly by the national swing that happened (knowing the national vote in
# advance); and this site's back-tested forecast on the last day (data/backtest_states.csv), states called by its chances
# as the Back-tests tab counts them.
dl = pd.read_csv('data/desart.csv')
lrX = lambda q: np.column_stack([np.ones(len(q)), q.previous, q.polls, q.home, q.terms])
lrfit = lambda q: np.linalg.lstsq(lrX(q), q.result.values, rcond=None)[0]
assert np.allclose(lrfit(dl[dl.year <= 2020]), [-27.423, 1.017, 0.524, 2.544, -0.988], atol=5e-4), 'refitted on 1996-2020 it should give his Table 2'
act = res.set_index(['year', 'state']).dem2; nat2 = res.groupby('year').nat2.first()
lastday = pd.read_csv('data/backtest_states.csv').set_index(['year', 'state'])
NAMES = {k: v['name'] for k, v in json.load(open('data/results_2024.json')).items() if len(k) == 2}
lr_rows, lr_all = [], []
for y in (2008, 2012, 2016, 2020, 2024):
    q = dl[dl.year == y].copy(); q['refit'] = lrX(q) @ lrfit(dl[dl.year < y]); pub = bool(q.published.notna().all())
    if y == 2020: assert (q.refit - q.published).abs().max() < 0.01, 'his 2020 forecast is the model fitted on 1996-2016'
    q['fc'] = q.published.astype(float) if pub else q.refit
    q['actual'] = [act[(y, s)] for s in q.state]; q['last'] = [act[(y - 4, s)] for s in q.state]; q['even'] = q['last'] + nat2[y] - nat2[y - 4]
    m = lastday.loc[y].loc[list(q.state)]; won = q.actual.values > 50
    score = lambda f, p=None: {'called': int(((f.values > 50 if p is None else p > 0.5) == won).sum()), 'miss': round(float(np.mean(np.abs(f.values - q.actual.values))), 2)}
    e = q.fc - q.actual
    lr_rows.append({'year': y, 'kind': 'published' if pub else 'backtest', **score(q.fc), 'wrong': sorted(NAMES[s] for s in q.state[(q.fc.values > 50) != won]),
                    'lean': round(float(e.mean()), 2), 'same_side': round(float(max((e > 0).mean(), (e < 0).mean())), 2),
                    'last': score(q['last']), 'even': score(q.even), 'site': score(m['mean'], m.p_dem.values)})
    lr_all.append(q.assign(site=m['mean'].values, site_p=m.p_dem.values))
A = pd.concat(lr_all); won = A.actual.values > 50
total = lambda f, p=None: {'called': int(((A[f].values > 50 if p is None else A[p].values > 0.5) == won).sum()), 'of': int(len(A)), 'miss': round(float(np.mean(np.abs(A[f] - A.actual))), 2)}
# his published forecasts, each from polls of the October before the election year (PS: Political Science & Politics,
# 2021 and 2025; 2016 as his 2016 APSA paper published it, run on all of October 2015's polls; a first version, presented
# in October 2015 before they were all in, had Donald Trump winning 305 to 233): who it had winning, the electoral votes
# each way, his Democratic share of the two-party vote; for 2024 his simulations' chance for the Republican as well
pub = [(2016, 'October 2015', 'Clinton', (285, 253), 50.3, None), (2020, 'October 2019', 'Biden', (350, 188), 54.8, None), (2024, 'October 2023', 'the Republican', (312, 226), 50.7, 0.74)]
WHO = {2016: ('Clinton', 'Trump'), 2020: ('Biden', 'Trump'), 2024: ('Harris', 'Trump')}
def won_ev(y):
    g = res[res.year == y]; d = int(g.ev[g.dem2 > 50].sum()); return ('D', d, int(g.ev.sum()) - d) if d > g.ev.sum() / 2 else ('R', int(g.ev.sum()) - d, d)
published = []
for y, polls, call, ev, share, p in pub:
    w, a, b = won_ev(y); call_party = 'R' if call in ('Trump', 'the Republican') else 'D'
    published.append({'year': y, 'polls': polls, 'call': call, 'ev': list(ev), 'share': share, 'p_call': p, 'winner': WHO[y][0 if w == 'D' else 1], 'won_ev': [a, b],
                      'dem': WHO[y][0], 'result_share': round(float(nat2[y]), 1), 'right': call_party == w})
out['long_range'] = {'published': published, 'right': sum(x['right'] for x in published), 'years': lr_rows,
                     'model': total('fc'), 'last': total('last'), 'even': total('even'), 'site': total('site', 'site_p')}
json.dump(out, open('data/research.json', 'w'), indent=1)
print('tilt', [(x['year'], x['state'], x['tilt']) for x in tilt], out['tilt']['toward_rep'], out['tilt']['toward_dem'], out['tilt']['typical'])
print('approval', {k: v for k, v in out['approval'].items() if k != 'points'})
print('movers', out['movers']['states'][:5], out['movers']['states'][-5:], out['movers']['toward_rep'], out['movers']['toward_dem'], out['movers']['close'], out['movers']['persist'], out['movers']['persist_1976'])
print('together', out['together'])
print('primary', {k: v for k, v in out['primary'].items() if k not in ('points', 'published')})
