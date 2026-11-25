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
json.dump(out, open('data/research.json', 'w'), indent=1)
print('tilt', [(x['year'], x['state'], x['tilt']) for x in tilt], out['tilt']['toward_rep'], out['tilt']['toward_dem'], out['tilt']['typical'])
print('approval', {k: v for k, v in out['approval'].items() if k != 'points'})
print('movers', out['movers']['states'][:5], out['movers']['states'][-5:], out['movers']['toward_rep'], out['movers']['toward_dem'], out['movers']['close'], out['movers']['persist'], out['movers']['persist_1976'])
print('together', out['together'])
print('primary', {k: v for k, v in out['primary'].items() if k not in ('points', 'published')})
